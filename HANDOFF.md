# HANDOFF.md: Model Handoff & Progress Ledger

## STATUS
- Current Task: O2 (Complete — SPIKES S1: Cowrie per-session persona investigation & PoC)
- Next Task: O3 (Experiment 0 implementation — waiting on Gate 0 prereqs & tags `eval-v1`, `exp0-v1`)

---

## DONE

### Task O2: SPIKES S1 — Cowrie Per-Session Persona (Opus / Architecture)

Investigation answering the core question: **Can Cowrie choose the persona (fake filesystem or identity) per session, after login, from our own code, without a deep fork?**

**Answer: YES. Decision: PLAN A (In-Process Subclass / Adapter Hook).**

---

### 1. Pinned Upstream Release
- **Pinned Tag**: `v3.1.6`
- **Pinned Commit Hash**: `ea9513eda9ea0dac05f6ace7db84ca95e0571501`
- **Source**: Cloned into `sensor/cowrie-src/` as a read-only study copy (configured in `.gitignore`).
- **Recorded in**: `DECISIONS.md` and `SPIKE_RESULTS.md`.

---

### 2. Source Code Path Audit & Exact Citations
Every subsystem was inspected with verified file paths and line numbers from `sensor/cowrie-src/` (tag `v3.1.6`):

1. **SSH Transport Setup and Banner**:
   - `src/cowrie/ssh/factory.py` lines 97–99: Server version banner read from `[ssh] version`, fallback `"SSH-2.0-OpenSSH_6.0p1 Debian-4+deb7u2"`.
   - `src/cowrie/ssh/factory.py` lines 107–179: `CowrieSSHFactory.buildProtocol(addr)` creates `HoneyPotSSHTransport`.
   - `src/cowrie/ssh/transport.py` lines 72–99: `connectionMade()` sends version string (`self.transport.write(self.ourVersionString + b"\r\n")`, line 91), sets `self.transportId = uuid.uuid4().hex[:12]` (line 79), and initializes session event emitter `transport_events(...)` (lines 100–116).
   - `src/cowrie/ssh/transport.py` lines 140–190: `dataReceived()` parses remote version identification and dispatches `cowrie.client.version` (lines 168–172).

2. **Key Exchange & HASSH Logging**:
   - `src/cowrie/ssh/transport.py` lines 258–281: `ssh_KEXINIT(packet)` unpacks client algorithm strings (`kexAlgs`, `keyAlgs`, `encCS`, `macCS`, `compCS`, `langCS`).
   - Line 265: Computes HASSH via `hasshAlgorithms, hassh = hassh_client(kexAlgs, encCS, macCS, compCS)`.
   - Lines 267–279: Dispatches event `cowrie.client.kex` containing `hassh`, `hasshAlgorithms`, `kexAlgs`, `keyAlgs`, `encCS`, `macCS`, `compCS`, `langCS`.

3. **Authentication & Login Acceptance**:
   - `src/cowrie/ssh/userauth.py` lines 40–245: `HoneyPotSSHUserAuthServer`.
   - Lines 134–149: `auth_password()` builds `credentials.UsernamePasswordIP(self.user, password, srcIp, events=...)` and calls `self.portal.login(c, srcIp, IConchUser)`.
   - `src/twisted/plugins/cowrie_plugin.py` lines 208–216: `factory.portal = portal.Portal(cowrie.shell.realm.HoneyPotRealm())` with credentials checkers `HoneypotPublicKeyChecker()`, `HoneypotPasswordChecker()`.
   - `src/cowrie/shell/realm.py` lines 22–27: `HoneyPotRealm.requestAvatar(avatarId, _mind, *interfaces)` instantiates virtual machine state:
     `serv = shellserver.CowrieServer(self)` and `user = shellavatar.CowrieUser(avatarId, serv)`.

4. **Shell Protocol Creation & Fake Filesystem Loading**:
   - `src/cowrie/shell/server.py` lines 23–53: `CowrieServer` holds emulated server state (`self.hostname`, `self.arch`, `self.fs`).
   - `src/cowrie/shell/avatar.py` lines 26–60: `CowrieUser(avatar.ConchUser)` registers `self.channelLookup[b"session"] = sshsession.HoneyPotSSHSession`. Lines 81–84 register the adapter:
     `components.registerAdapter(shellsession.SSHSessionForCowrieUser, CowrieUser, ISession)`.
   - `src/cowrie/shell/session.py` lines 48–87: `SSHSessionForCowrieUser.__init__()` takes `avatar`, reads `self.server = avatar.server`, sets environment (`PATH`, `USER`, `HOME`), and calls `self.server.initFileSystem(self.avatar.home)` (line 81).
   - `src/cowrie/shell/fs.py` lines 126–161: `HoneyPotFilesystem.__init__()` loads base tree via `honeyfs.get_tree()` (`src/cowrie/core/honeyfs.py` lines 65–96 from `[shell] filesystem` or bundled `fs.pickle`). If `contents_path` is configured, calls `init_honeyfs()` (lines 173–187) which overlays real files onto matching virtual nodes (`f[A_REALFILE] = realfile_path`).
   - `src/cowrie/shell/session.py` lines 88–94: `openShell()` instantiates `insults.LoggingServerProtocol(protocol.HoneyPotInteractiveProtocol, self)`.
   - `src/cowrie/shell/protocol.py` lines 68–72: `HoneyPotBaseProtocol` assigns `self.hostname = self.user.server.hostname` and `self.fs = self.user.server.fs`.
   - `src/cowrie/shell/honeypot.py` line 1340: Shell prompt is rendered dynamically as `f"{username}@{self.protocol.hostname}:{cwd}"`.

5. **Command Dispatch**:
   - `src/cowrie/shell/honeypot.py` lines 932–1250: `runCommand()`, `_run_compound()`, `_run_expanded()`.
   - Lines 1211–1215: `cmdclass = self.protocol.getCommand(cmd, environ.get("PATH", "").split(":"), self.cwd)`.
   - `src/cowrie/shell/protocol.py` lines 246–270: `getCommand()` checks `self.commands` (built-in command classes), `self.fs` for executable binaries/scripts (`scriptcmd()`), and `txtcmds_path`.
   - Dispatches `cowrie.command.failed` on missing command (lines 1216–1220) or executes the command protocol.

6. **Proxy and Backend Pool Selection**:
   - `src/twisted/plugins/cowrie_plugin.py` lines 162–216: Reads `backend = CowrieConfig.get("honeypot", "backend", fallback="shell")`.
   - If `backend == "proxy"`, routes via `cowrie.ssh_proxy.server_transport.FrontendSSHTransport` and `cowrie.ssh_proxy.userauth.ProxySSHAuthServer`.
   - If `proxy_backend == "pool"`, initializes `PoolHandler` (`src/cowrie/pool_interface/handler.py`).
   - Default Cowrie selects backend statically at daemon launch in `CowrieServiceMaker.makeService()`.

---

### 3. Proof-of-Concept & Verification
- **Implementation**: [`sensor/spike_s1_poc.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/sensor/spike_s1_poc.py)
- **Unit Tests**: [`sensor/test_spike_s1_poc.py`](file:///c:/Users/abhip/OneDrive/Documents/mini%20project/sensor/test_spike_s1_poc.py)
- **Mechanism**:
  - Implemented `AdaptiveSSHSession(shellsession.SSHSessionForCowrieUser)`.
  - When a channel is opened post-authentication, the adapter inspects the active peer socket (`avatar.conn.transport.transport.getPeer().port`).
  - **Odd Port Rule (e.g. 54321)**: Assigns Persona 1 (T2 Web Server, `web-srv-01`, Ubuntu 22.04 motd, `/etc/persona`).
  - **Even Port Rule (e.g. 54322)**: Assigns Persona 2 (T1 Generic Server, `generic-srv-02`, Debian 12 motd, `/etc/persona`).
- **Transcript from Terminal Execution**:
  ```
  ======================================================================
  SPIKE S1 PoC: Cowrie Per-Session Persona Switching
  ======================================================================

  --- Session A: Connecting from port 54321 (ODD) ---
  Assigned Persona : Persona 1 (T2 Web Server)
  Command `hostname` output      : web-srv-01
  Command `cat /etc/persona` out : PERSONA_1: Production Web Server (Ubuntu 22.04 / Nginx)
  Command `cat /etc/motd` output : Welcome to Ubuntu 22.04 LTS (Web Cluster Node 1)

  --- Session B: Connecting from port 54322 (EVEN) ---
  Assigned Persona : Persona 2 (T1 Generic Server)
  Command `hostname` output      : generic-srv-02
  Command `cat /etc/persona` out : PERSONA_2: Edge Gateway (Debian 12 / Minimal)
  Command `cat /etc/motd` output : Welcome to Debian GNU/Linux 12 (Minimal Sensor)

  ======================================================================
  RESULT: SUCCESS - Plan A (in-process hook) is fully verified!
    Session A (odd port) saw Persona 1 (Ubuntu 22.04 web-srv-01).
    Session B (even port) saw Persona 2 (Debian 12 generic-srv-02).
  ======================================================================
  ```
- **Pytest Output**: `2 passed in 4.77s`.

---

### 4. Technical Spike Decisions
- **Hook Point**: Twisted Conch session adapter boundary (`components.registerAdapter(AdaptiveSSHSession, CowrieUser, ISession)`).
- **Lines of Cowrie core that must change**: **0 lines**. No fork needed.
- **Sufficiency**: A subclass of `SSHSessionForCowrieUser` (or custom Realm) is completely sufficient.
- **Merge-Pain Risk**: **Near Zero**. Because no upstream Cowrie files are modified, Cowrie can be upgraded cleanly without merge conflicts.
- **Decision**: **Plan A (achieved)**. Recorded in `DECISIONS.md` and `SPIKE_RESULTS.md`.

---

## FILES
- `.gitignore` (modified — added `sensor/cowrie-src/`)
- `DECISIONS.md` (modified — recorded pinned Cowrie v3.1.6 and Spike S1 Plan A decision)
- `SPIKE_RESULTS.md` (modified — recorded Spike S1 outcome and evidence)
- `sensor/spike_s1_poc.py` (new — reproducible PoC script)
- `sensor/test_spike_s1_poc.py` (new — pytest test suite for S1 PoC)
- `HANDOFF.md` (modified — updated progress and findings)

---

## COMMANDS AND OUTCOMES
1. `git ls-remote --tags https://github.com/cowrie/cowrie.git`: Pinned release tag `v3.1.6` (commit `ea9513eda9ea0dac05f6ace7db84ca95e0571501`).
2. `git clone --depth 1 --branch v3.1.6 https://github.com/cowrie/cowrie.git sensor/cowrie-src`: Cloned study copy.
3. `wsl /tmp/cowrie-lab-venv/bin/python3 sensor/spike_s1_poc.py`: Both sessions assigned distinct personas (Plan A verified).
4. `wsl /tmp/cowrie-lab-venv/bin/python3 -m pytest sensor/test_spike_s1_poc.py`: `2 passed in 4.77s`.

---

## TODO(verify)
- None remaining for Spike S1.
- In S3 Part 2 (when downloading 2-3 event days from `data_all.zip`), confirm dataset descriptor regarding the 52 calendar day span vs. documented "50 days".

---

## QUESTIONS FOR OPUS
*(All current Opus questions for S1 are resolved: Plan A is accepted with 0 core changes).*

---

## QUESTIONS FOR HUMAN
- Spike S1 (Plan A in-process persona switching) and Spike S3 Part 1 (base rates 3.23% on 38.1M sessions) are complete and recorded in `SPIKE_RESULTS.md` and `DECISIONS.md`.
- Next is **Task O3: Experiment 0** (`EXPERIMENT0.md`). Per `PROMPTS.md` and `AGENTS.md`:
  - Before starting O3, the human should apply git tags `eval-v1` and `exp0-v1`.
  - Please confirm readiness to proceed to Task O3.
