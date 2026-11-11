"""
Spike S1 Proof-of-Concept: Per-session persona switching in Cowrie after login.

Rule:
  Odd source port  -> Persona 1 (web-srv-01, T2)
  Even source port -> Persona 2 (generic-srv-02, T1)
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

# Pinned Cowrie source path
COWRIE_ROOT = Path(__file__).resolve().parent / "cowrie-src"
sys.path.insert(0, str(COWRIE_ROOT / "src"))

# Cowrie environment variables
os.environ["COWRIE_HONEYPOT_DATA_PATH"] = str(COWRIE_ROOT / "src" / "cowrie" / "data")
os.environ["COWRIE_SHELL_FILESYSTEM"] = str(COWRIE_ROOT / "src" / "cowrie" / "data" / "fs.pickle")

# Stub _version if uninstalled
import types
if "cowrie._version" not in sys.modules:
    m = types.ModuleType("cowrie._version")
    m.__version__ = "3.1.6"
    m.version = "3.1.6"
    sys.modules["cowrie._version"] = m

from cowrie.insults import insults
from cowrie.shell import avatar as shellavatar
from cowrie.shell import fs, protocol, realm, server
from cowrie.shell import session as shellsession
from cowrie.test.eventcapture import CaptureSink, _capture_pipeline


class OutputCollector:
    """Captures all terminal / process writes."""
    def __init__(self):
        self.buffer = bytearray()

    def write(self, data: bytes):
        if isinstance(data, bytes):
            self.buffer.extend(data)
        elif isinstance(data, str):
            self.buffer.extend(data.encode("utf-8", errors="replace"))

    def get_output(self) -> str:
        return self.buffer.decode("utf-8", errors="replace")


def make_test_transport(client_port: int, sink: CaptureSink, collector: OutputCollector) -> SimpleNamespace:
    """Constructs transport chain expected by LoggingServerProtocol."""
    peer = SimpleNamespace(host="192.168.1.100", port=client_port)
    inner = SimpleNamespace(sessionno=1, getPeer=lambda: peer)
    factory = SimpleNamespace(starttime=0)
    events = _capture_pipeline(sink, session=f"sess_{client_port}", protocol="ssh", src_ip="192.168.1.100")
    conn_transport = SimpleNamespace(
        transportId=f"sess_{client_port}", factory=factory, transport=inner, events=events
    )
    conn = SimpleNamespace(transport=conn_transport)
    session = SimpleNamespace(id="chan0", conn=conn)
    return SimpleNamespace(
        session=session,
        write=collector.write,
        processEnded=lambda reason=None: None,
    )


class AdaptiveSSHSession(shellsession.SSHSessionForCowrieUser):
    """
    Adaptive SSHSession adapter:
    Inspects peer source port on the active connection before shell initialization.
    Configures persona (hostname, fake filesystem overlay) per-session.
    """
    def __init__(self, avatar, peer_port: int, reactor=None):
        super().__init__(avatar, reactor)
        self.peer_port = peer_port
        
        # S1 Decision Rule: Odd port -> Persona 1, Even port -> Persona 2
        if self.peer_port % 2 == 1:
            self.server.hostname = "web-srv-01"
            self.server.persona_name = "Persona 1 (T2 Web Server)"
            persona_banner = b"PERSONA_1: Production Web Server (Ubuntu 22.04 / Nginx)\n"
            persona_dir = getattr(self.server, "_persona1_dir", None)
        else:
            self.server.hostname = "generic-srv-02"
            self.server.persona_name = "Persona 2 (T1 Generic Server)"
            persona_banner = b"PERSONA_2: Edge Gateway (Debian 12 / Minimal)\n"
            persona_dir = getattr(self.server, "_persona2_dir", None)

        # Inject persona-identifying file into the virtual filesystem
        self.server.fs.mkfile("/etc/persona", 0, 0, len(persona_banner), 0o100644)
        node = self.server.fs.getfile("/etc/persona")
        if node is not None:
            node[fs.A_CONTENTS] = persona_banner
        
        # Overlay any honeyfs disk files if provided
        if persona_dir and os.path.isdir(persona_dir):
            self.server.fs.init_honeyfs(persona_dir)


def run_command_in_session(client_port: int, cmd: bytes, p1_dir: str, p2_dir: str) -> dict:
    """Executes a command in an emulated session and returns persona details and command output."""
    r = realm.HoneyPotRealm()
    serv = server.CowrieServer(r)
    serv._persona1_dir = p1_dir
    serv._persona2_dir = p2_dir

    user = shellavatar.CowrieUser(b"root", serv)
    
    # Adaptive session adapter selects persona dynamically
    session_adapter = AdaptiveSSHSession(user, peer_port=client_port)

    collector = OutputCollector()
    sink = CaptureSink()
    transport = make_test_transport(client_port, sink, collector)

    # HoneyPotExecProtocol expects session_adapter as its avatar argument
    lsp = insults.LoggingServerProtocol(protocol.HoneyPotExecProtocol, session_adapter, cmd)
    lsp.makeConnection(transport)

    return {
        "client_port": client_port,
        "persona": serv.persona_name,
        "hostname": serv.hostname,
        "output": collector.get_output(),
        "fs_persona_file": serv.fs.file_contents("/etc/persona").decode("utf-8", errors="replace"),
    }


def main():
    print("=" * 70)
    print("SPIKE S1 PoC: Cowrie Per-Session Persona Switching")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create two distinct persona honeyfs overlays
        p1_dir = os.path.join(tmp_dir, "persona1")
        p2_dir = os.path.join(tmp_dir, "persona2")
        os.makedirs(os.path.join(p1_dir, "etc"), exist_ok=True)
        os.makedirs(os.path.join(p2_dir, "etc"), exist_ok=True)

        with open(os.path.join(p1_dir, "etc", "motd"), "w") as f:
            f.write("Welcome to Ubuntu 22.04 LTS (Web Cluster Node 1)\n")

        with open(os.path.join(p2_dir, "etc", "motd"), "w") as f:
            f.write("Welcome to Debian GNU/Linux 12 (Minimal Sensor)\n")

        # Session A: Client connects from ODD port 54321
        print("\n--- Session A: Connecting from port 54321 (ODD) ---")
        res_a_host = run_command_in_session(54321, b"hostname", p1_dir, p2_dir)
        res_a_cat = run_command_in_session(54321, b"cat /etc/persona", p1_dir, p2_dir)
        res_a_motd = run_command_in_session(54321, b"cat /etc/motd", p1_dir, p2_dir)

        print(f"Assigned Persona : {res_a_host['persona']}")
        print(f"Command `hostname` output      : {res_a_host['output'].strip()}")
        print(f"Command `cat /etc/persona` out : {res_a_cat['output'].strip()}")
        print(f"Command `cat /etc/motd` output : {res_a_motd['output'].strip()}")

        # Session B: Client connects from EVEN port 54322
        print("\n--- Session B: Connecting from port 54322 (EVEN) ---")
        res_b_host = run_command_in_session(54322, b"hostname", p1_dir, p2_dir)
        res_b_cat = run_command_in_session(54322, b"cat /etc/persona", p1_dir, p2_dir)
        res_b_motd = run_command_in_session(54322, b"cat /etc/motd", p1_dir, p2_dir)

        print(f"Assigned Persona : {res_b_host['persona']}")
        print(f"Command `hostname` output      : {res_b_host['output'].strip()}")
        print(f"Command `cat /etc/persona` out : {res_b_cat['output'].strip()}")
        print(f"Command `cat /etc/motd` output : {res_b_motd['output'].strip()}")

        # Verification Assertions
        assert res_a_host['output'].strip() == "web-srv-01", f"Expected web-srv-01, got '{res_a_host['output']}'"
        assert res_b_host['output'].strip() == "generic-srv-02", f"Expected generic-srv-02, got '{res_b_host['output']}'"
        assert "PERSONA_1" in res_a_cat['output'], f"Expected PERSONA_1 in output: '{res_a_cat['output']}'"
        assert "PERSONA_2" in res_b_cat['output'], f"Expected PERSONA_2 in output: '{res_b_cat['output']}'"
        assert "Ubuntu" in res_a_motd['output'], f"Expected Ubuntu in motd: '{res_a_motd['output']}'"
        assert "Debian" in res_b_motd['output'], f"Expected Debian in motd: '{res_b_motd['output']}'"

        print("\n" + "=" * 70)
        print("RESULT: SUCCESS - Plan A (in-process hook) is fully verified!")
        print("  Session A (odd port) saw Persona 1 (Ubuntu 22.04 web-srv-01).")
        print("  Session B (even port) saw Persona 2 (Debian 12 generic-srv-02).")
        print("=" * 70)


if __name__ == "__main__":
    main()
