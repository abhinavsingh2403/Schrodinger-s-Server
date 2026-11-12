"""
Sensor Production Adaptive Adapter.
Pre-registered in SPEC.md Section 5.1, Section 5.3 and Spike S1.

Provides:
- PersonaManager: manages filesystem overlays, MOTD, banners, and decoy assets
  while enforcing strict OS/distro identity coherence across tiers (SPEC Risk R8).
- AdaptiveSessionAdapter: connects Cowrie session events (handshake, auth, commands)
  to the Gatekeeper DecisionEngine, executing dynamic upward-only tier escalation
  with fail-cheap defaults to T1.

INTEGRATION STATUS & CAVEAT:
- End-to-end integration with live Cowrie in-process execution is proven exclusively
  by `sensor/spike_s1_poc.py` on systems with Twisted Conch and Cowrie runtime present.
- In environments without Twisted Conch installed (e.g. standard Windows dev venv),
  `CowrieSSHSessionAdapter` raises RuntimeError and is NOT an integration test pass.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sensor.adaptive")

TIER_ORDER: Dict[str, int] = {"T1": 1, "T2": 2, "T3": 3}

# Optional Cowrie integration: dynamically detect Cowrie Twisted environment
COWRIE_ROOT = Path(__file__).resolve().parent / "cowrie-src"
if COWRIE_ROOT.exists():
    _src = str(COWRIE_ROOT / "src")
    if _src not in sys.path:
        sys.path.insert(0, _src)

COWRIE_AVAILABLE = False
try:
    import types
    if "cowrie._version" not in sys.modules:
        m = types.ModuleType("cowrie._version")
        m.__version__ = "3.1.6"
        m.version = "3.1.6"
        sys.modules["cowrie._version"] = m
    from cowrie.shell import session as shellsession
    from cowrie.shell import fs
    COWRIE_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    shellsession = None  # type: ignore
    fs = None  # type: ignore


@dataclass
class Persona:
    """System persona configuration for a given tier."""
    tier: str
    distro: str
    kernel_release: str
    hostname: str
    banner: str
    fs_dir: str


class PersonaManager:
    """
    Manages persona environments and filesystem overlays across tiers.
    Ensures OS coherence per SPEC.md Section 5.1 and identity.yaml.
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        identity_path: Optional[str] = None,
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent / "personas"
        self.identity_path = identity_path or self._find_identity_file()
        self.identity = self._load_identity()
        self.personas: Dict[str, Persona] = {}
        self._init_personas()

    def _find_identity_file(self) -> str:
        candidates = [
            Path(__file__).resolve().parent / "identity.yaml",
            Path(__file__).resolve().parent.parent / "config" / "identity.yaml",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return str(candidates[0])

    def _load_identity(self) -> Dict[str, Any]:
        """Loads identity configuration from YAML or provides hardcoded baseline."""
        defaults = {
            "distro": "Ubuntu",
            "release": "22.04.3 LTS",
            "kernel": "5.15.0-88-generic",
            "hostname": "srv-app-01",
            "banner": "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.4",
        }
        if os.path.exists(self.identity_path):
            try:
                with open(self.identity_path, "r", encoding="utf-8") as f:
                    content = f.read()
                for line in content.splitlines():
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k in defaults:
                            defaults[k] = v
            except Exception as e:
                logger.warning("Could not parse identity.yaml (%s); using defaults", e)
        return defaults

    def _init_personas(self) -> None:
        """Create filesystem templates for T1 and T2 preserving OS identity."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

        for tier in ("T1", "T2", "T3"):
            tier_fs = self.base_dir / tier.lower()
            tier_fs.mkdir(parents=True, exist_ok=True)

            # Common OS structure
            for sub in ("bin", "etc", "var/log", "home/ubuntu", "root"):
                (tier_fs / sub).mkdir(parents=True, exist_ok=True)

            # Unified identity markers (identical across all tiers)
            with open(tier_fs / "etc" / "hostname", "w", encoding="utf-8") as f:
                f.write(f"{self.identity['hostname']}\n")

            with open(tier_fs / "etc" / "motd", "w", encoding="utf-8") as f:
                f.write(
                    f"Welcome to {self.identity['distro']} {self.identity['release']} "
                    f"({self.identity['kernel']})\n\n"
                    f" * Documentation:  https://help.ubuntu.com\n"
                    f" * Management:     https://landscape.canonical.com\n\n"
                )

            # Tier 2 enriched honeypot filesystem additions (SPEC Section 5.1)
            if tier == "T2":
                (tier_fs / "var" / "www" / "html").mkdir(parents=True, exist_ok=True)
                with open(tier_fs / "var" / "www" / "html" / "index.html", "w", encoding="utf-8") as f:
                    f.write("<html><body><h1>Maintenance Mode</h1></body></html>\n")
                (tier_fs / "opt" / "deploy").mkdir(parents=True, exist_ok=True)
                with open(tier_fs / "opt" / "deploy" / "config.env", "w", encoding="utf-8") as f:
                    f.write("DB_HOST=10.0.0.4\nDB_USER=app_user\n")

            self.personas[tier] = Persona(
                tier=tier,
                distro=self.identity["distro"],
                kernel_release=self.identity["kernel"],
                hostname=self.identity["hostname"],
                banner=self.identity["banner"],
                fs_dir=str(tier_fs),
            )

    def get_persona(self, tier: str) -> Persona:
        """Retrieve persona configuration for a given tier (defaults to T1)."""
        return self.personas.get(tier.upper(), self.personas["T1"])


class AdaptiveSessionAdapter:
    """
    Stateful adapter wrapping an incoming SSH session.
    Invokes Gatekeeper DecisionEngine and manages persona escalation.
    """

    def __init__(
        self,
        visitor_ip: str,
        session_id: str,
        decision_engine: Any,
        persona_manager: Optional[PersonaManager] = None,
    ) -> None:
        self.visitor_ip = visitor_ip
        self.session_id = session_id
        self.decision_engine = decision_engine
        self.persona_manager = persona_manager or PersonaManager()

        self.current_tier = "T1"
        self.commands_history: List[str] = []
        self.failed_auth_count = 0
        self.auth_success = False
        self.client_version = ""
        self.hassh = ""

    def get_active_persona(self) -> Persona:
        """Returns the currently active persona."""
        return self.persona_manager.get_persona(self.current_tier)

    def escalate_to(self, target_tier: str) -> bool:
        """
        Escalates the session to target_tier if target_tier > current_tier.
        Enforces the monotone upward-only tier progression rule.
        """
        target = target_tier.upper()
        if target not in TIER_ORDER:
            return False

        if TIER_ORDER[target] > TIER_ORDER[self.current_tier]:
            logger.info(
                "Session %s (%s): Escalating tier from %s to %s",
                self.session_id,
                self.visitor_ip,
                self.current_tier,
                target,
            )
            self.current_tier = target
            return True
        return False

    def on_kex_completed(
        self,
        client_version: str,
        hassh: str,
        kex_algs: Optional[List[str]] = None,
        key_algs: Optional[List[str]] = None,
    ) -> None:
        """Event handler: SSH Key Exchange completed (Stage S1)."""
        self.client_version = client_version
        self.hassh = hassh
        features = {
            "client_version": client_version,
            "hassh": hassh,
            "kex_algs_count": len(kex_algs or []),
            "key_algs_count": len(key_algs or []),
        }
        self._evaluate_stage("S1", features)

    def on_auth_completed(
        self,
        success: bool,
        failed_count: int = 0,
        username: str = "root",
    ) -> None:
        """Event handler: User authentication attempt finished (Stage S2)."""
        self.auth_success = success
        self.failed_auth_count = failed_count
        features = {
            "login_success": 1 if success else 0,
            "n_login_failed": failed_count,
            "distinct_usernames_tried": 1 if username else 0,
            "time_to_first_success": 1.2 if success else 0.0,
        }
        self._evaluate_stage("S2", features)

    def on_command_received(self, cmd: str) -> None:
        """Event handler: Shell command input received (Stage S4 or S5)."""
        clean_cmd = cmd.strip()
        self.commands_history.append(clean_cmd)

        stage = "S4" if len(self.commands_history) == 1 else "S5"
        features = {
            "cmd_length": len(clean_cmd),
            "token_count": len(clean_cmd.split()),
            "chaining_ops_count": clean_cmd.count(";") + clean_cmd.count("&&") + clean_cmd.count("|"),
            "distinct_cmd_ratio": len(set(self.commands_history)) / len(self.commands_history),
        }
        self._evaluate_stage(stage, features)

    def on_session_closed(self, value_label: Optional[int] = None) -> None:
        """Event handler: SSH session terminated; persists completed session to visitor memory."""
        if not self.decision_engine:
            return
        try:
            if hasattr(self.decision_engine, "record_session"):
                label = value_label if value_label is not None else (1 if len(self.commands_history) >= 5 else 0)
                self.decision_engine.record_session(
                    source_ip=self.visitor_ip,
                    tier_served=self.current_tier,
                    value_label=label,
                )
        except Exception:
            pass

    def _evaluate_stage(self, stage: str, features: Dict[str, Any]) -> None:
        """Queries the decision engine and applies escalation."""
        if not self.decision_engine:
            return

        try:
            resp = self.decision_engine.decide(
                session_id=self.session_id,
                source_ip=self.visitor_ip,
                stage=stage,
                features=features,
                current_tier=self.current_tier,
            )
            target_tier = resp.get("target_tier") or resp.get("tier", "T1")
            self.escalate_to(target_tier)
        except Exception as exc:
            # Fail-cheap: remain in current tier or T1, never crash connection
            logger.warning("Decision engine query failed (%s); maintaining %s", exc, self.current_tier)


if COWRIE_AVAILABLE and shellsession is not None:
    class CowrieSSHSessionAdapter(shellsession.SSHSessionForCowrieUser):
        """
        Twisted Conch session adapter for production Cowrie honeypot.
        Bridges Cowrie SSH session events directly to AdaptiveSessionAdapter
        and applies persona filesystem overlays upon tier escalation.
        """

        def __init__(self, avatar, decision_engine: Any, reactor=None):
            super().__init__(avatar, reactor)
            peer = avatar.conn.transport.transport.getPeer()
            visitor_ip = str(getattr(peer, "host", "127.0.0.1"))
            session_id = str(getattr(avatar.conn.transport, "transportId", "sess_unknown"))

            self.persona_manager = PersonaManager()
            self.adapter = AdaptiveSessionAdapter(
                visitor_ip=visitor_ip,
                session_id=session_id,
                decision_engine=decision_engine,
                persona_manager=self.persona_manager,
            )

            # Apply initial T1 persona
            initial_p = self.adapter.get_active_persona()
            self.server.hostname = initial_p.hostname
            self._apply_fs_overlay(initial_p)

        def _apply_fs_overlay(self, persona: Persona) -> None:
            """Overlays persona identity files onto the Cowrie virtual filesystem."""
            if fs is not None and hasattr(self.server, "fs"):
                try:
                    motd_content = f"Welcome to {persona.distro} ({persona.kernel_release})\n".encode("utf-8")
                    self.server.fs.mkfile("/etc/motd", 0, 0, len(motd_content), 0o100644)
                    node = self.server.fs.getfile("/etc/motd")
                    if node is not None:
                        node[fs.A_CONTENTS] = motd_content
                except Exception as e:
                    logger.debug("Failed applying Cowrie fs overlay: %s", e)
else:
    class CowrieSSHSessionAdapter:  # type: ignore
        """Placeholder when running in environments without Twisted Conch."""
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Twisted Conch and Cowrie must be installed to instantiate CowrieSSHSessionAdapter.")
