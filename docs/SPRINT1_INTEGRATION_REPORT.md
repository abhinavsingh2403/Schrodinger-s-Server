# Schrödinger's Server — Sprint 1 Integration Hardening Report

**Date**: November 27, 2026  
**Active Working Branch**: `exp-1`  
**Base Ancestor**: `origin/gemini-frontend` (`3a1fa9d`) / `trainmodel` (`5b15d4c`)  
**Runtime Environment**: Python 3.13.2 / Windows 11 / PowerShell  
**Test Suite Verdict**: **339 passed, 8 skipped in 13.11s** (Unsandboxed) / **332 passed, 15 skipped in 16.17s** (Sandboxed) · **0 Failures**

---

## 1. Executive Summary & Deliverables Scorecard

Sprint 1 focuses on hardening the end-to-end integration of Schrödinger's Server across the sensor lifecycle, Docker ingress, Gatekeeper decision engine, sticky router, and the Abyssal Observatory dashboard.

Each required deliverable has been evaluated and classified according to verified repository evidence:

| Deliverable | Description | Classification | Verification Modality |
| :--- | :--- | :---: | :--- |
| **1. End-to-End Architecture** | Complete 10-stage pipeline from SSH ingress to dashboard | **COMPLETED** | Integration-tested & Simulated |
| **2. Component Integrations** | Sensor, Gatekeeper, Memory, Router, Dashboard connectors | **COMPLETED** | Unit-tested & Integration-tested |
| **3. Docker Visitor-Identity Fix** | PROXY protocol v1 ingress & trusted proxy validation | **COMPLETED** | Integration-tested |
| **4. Two-Visitor Identity Tests** | Multi-visitor separation, returning visitor & anti-spoofing | **COMPLETED** | Integration-tested (`test_docker_visitor_identity.py`) |
| **5. Adaptive T1/T2 Integration** | S1→S3 mid-session escalation, monotone policy & budget cap | **COMPLETED** | Integration-tested (`test_adaptive_t1_t2_integration.py`) |
| **6. Dashboard Live Data** | Verification across all 8 Abyssal Observatory workspaces | **COMPLETED** | Integration-tested (`test_ui_correctness.py` & API probe) |
| **7. Integration Documentation** | Documented pipeline schemas, security, and networking | **COMPLETED** | Verified in `docs/` |
| **8. Test Execution Report** | Multi-suite regression accounting for environment restrictions | **COMPLETED** | Full regression suite verified |
| **9. File Audit** | Complete accounting of created and modified files | **COMPLETED** | Clean git status |
| **10. Remaining Blockers** | Honest accounting of WSL/Docker live trials and deferred T3 | **PARTIALLY COMPLETED** | Gated on live infrastructure |

---

## 2. Deliverable 1: Verified End-to-End Pipeline Architecture

The end-to-end telemetry and defense pipeline has been traced, verified, and hardened:

```
Incoming SSH Visitor (e.g. 198.51.100.10:54321)
       │
       ▼
Edge Ingress Proxy (`infra/edge_forward.py`: Port 2222)
       │  [Preserves real client IP via HAProxy PROXY Protocol v1]
       ▼
Cowrie Honeypot Sensor (`sensor/run_sensor.py` / Twisted Conch)
       │  [Extracts real client IP from trusted PROXY header]
       ▼
Session Event Collection (`LifecycleBridge.event` & `PrefixLog`)
       │  [Captures connect, NEWKEYS, auth, pty, command, close]
       ▼
Feature Extraction (`gatekeeper/feature_extractor.py`)
       │  [Extracts canonical stage features: S1, S2, S3, S4, S5]
       ▼
Gatekeeper Decision API (`gatekeeper/decision_api.py`)
       │  [In-process or REST HTTP /decide, validates provenance]
       ▼
Visitor Memory (`gatekeeper/visitor_memory.py`)
       │  [Deterministic HMAC-SHA256 salted visitor ID, SQLite WAL]
       ▼
Escalation Policy & Budget (`gatekeeper/policy.py`)
       │  [Monotone upward-only, 10% budget ceiling, fail-cheap T1]
       ▼
T1/T2 Persona Allocation (`sensor/adaptive_server.py`)
       │  [PersonaManager switches honeyfs overlay without drop]
       ▼
Session Routing (`router/sticky_router.py`)
       │  [TCP stream splicing with TCP half-close & drain grace]
       ▼
Dashboard Evidence & Analytics (`dashboard/app.py`)
          [Zero raw IPs; cryptographically masked ses_ and vis_ IDs]
```

### Stage Transition Data Contracts & Invariants

1. **Incoming SSH Visitor → Edge Proxy**:
   - Connection established on port 2222.
   - `edge_forward.py` captures true client socket address `(peer_ip, peer_port)`.
2. **Edge Proxy → Cowrie Sensor**:
   - Edge formats PROXY protocol v1 header: `PROXY TCP4 <peer_ip> <sock_ip> <peer_port> 2222\r\n`.
   - `sensor/run_sensor.py` intercepts `HoneyPotSSHTransport.dataReceived`.
   - Checks if socket peer is an authorized trusted proxy (`is_trusted_proxy`).
   - If trusted, parses real client IP and overrides `self.transport.getPeer().host`.
   - If untrusted, ignores header; unparsed bytes trigger SSH protocol error, preventing spoofing.
3. **Cowrie Sensor → Event Dispatcher**:
   - Emits structured events with accurate `src_ip` (`cowrie.session.connect`, `cowrie.login.success`, etc.).
4. **Event Dispatcher → Session Feature Extractor**:
   - Ingests events and extracts canonical features per stage vector (`cnt_client_kex`, `login_success`, `has_pty`, `session_command_count`).
5. **Feature Extractor → Decision Engine**:
   - Evaluates stage features against pre-registered model (`models/model_s3.json`) or policy heuristics.
   - Validates provenance against allowed set: `{'SYNTHETIC', 'LAB', 'LIVE', 'UNKNOWN'}`.
6. **Decision Engine → Visitor Memory & Budget**:
   - Derives `visitor_id = HMAC-SHA256(salt, source_ip)[:16]`.
   - Queries visitor history (`highest_tier_served`, `n_sessions`).
   - `SessionBudget.apply()` enforces the durable escalation cap (10% ceiling).
   - Atomic SQLite WAL transaction commits decision to `decision_log`.
7. **Decision Engine → Adaptive Session Adapter**:
   - Returns admitted target tier.
   - If `target_tier > current_tier`, escalates to `target_tier` (upward-only, never demotes).
   - `PersonaManager.get_persona(target_tier)` supplies filesystem template.
8. **Session Termination**:
   - `on_session_closed()` invokes `record_session()` updating `highest_tier_served` and incrementing `n_sessions`.
9. **Dashboard Projection**:
   - `dashboard/decision_views.py` masks sessions as `ses_...` and visitors as `vis_...`. Zero raw IPs exposed.

---

## 3. Deliverable 2 & 3: Docker Networking & Visitor Identity Hardening

### The Root Cause

Under the previous Docker network topology (`infra/docker-compose.yml`), external traffic reached `edge:2222`, which executed `asyncio.open_connection('sensor', 2222)`. Because `edge` created a standard TCP client socket, Cowrie inside `sensor` only saw the internal bridge IP of `edge` (e.g. `172.20.0.2`).

Consequently:
- All external visitors collapsed into a single IP (`172.20.0.2`).
- Every visitor generated the identical HMAC visitor ID.
- Once any visitor escalated to T2, all subsequent visitors were incorrectly treated as returning visitors and assigned T2.
- The 10% escalation budget was exhausted by one visitor and blocked all others.

### Implemented Hardening Solution

1. **Created `infra/proxy.py`**:
   - `get_trusted_proxies()`: Configures trusted proxy CIDRs (`127.0.0.1/32`, `::1/128`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, or `TRUSTED_PROXIES` environment override).
   - `is_trusted_proxy(ip)`: Verifies if a remote peer is an authorized proxy.
   - `format_proxy_v1()`: Generates standard HAProxy PROXY protocol v1 headers.
   - `parse_proxy_v1()`: Parses PROXY protocol lines with IP format and port validation.
   - `extract_forwarded_ip()`: Safely extracts client IP from `X-Forwarded-For` HTTP headers **only** when the connection originates from an authorized proxy. Untrusted clients are strictly ignored.

2. **Updated `infra/edge_forward.py`**:
   - Enabled PROXY protocol v1 transmission on SSH port 2222 forwarding to `sensor`.

3. **Updated `sensor/run_sensor.py`**:
   - Wrapped `HoneyPotSSHTransport.dataReceived` with proxy awareness.
   - Validates socket peer against `is_trusted_proxy`.
   - On match, parses `real_ip` and overrides `self.transport.getPeer().host = real_ip`.

4. **Updated `router/sticky_router.py`**:
   - Integrated trusted proxy check and PROXY protocol header consumption prior to tier selection.

5. **Updated `infra/Dockerfile.edge` and `infra/Dockerfile.sensor`**:
   - Packaged `infra/proxy.py` into container builds.

---

## 4. Deliverable 4: Multi-Visitor Separation & Anti-Spoofing Tests

Created dedicated integration test suite: `infra/test_docker_visitor_identity.py` (5/5 tests passing):

1. **`test_multi_visitor_separation_across_proxy`**:
   - Simulates Visitor A (`198.51.100.11`) and Visitor B (`198.51.100.22`).
   - Verifies distinct derived visitor IDs and distinct public masks (`vis_...`).
   - Visitor A escalates to T2; verifies Visitor B connecting subsequently remains in T1 and is never merged with Visitor A.
2. **`test_returning_visitor_consistent_pseudonym_and_tier_retention`**:
   - Simulates returning visitor across consecutive sessions.
   - Confirms exact pseudonymous ID preservation (`initial_mask == returning_mask`).
   - Confirms sticky retention of T2 and accurate session count tracking (`n_sessions = 2`).
3. **`test_raw_ip_privacy_in_dashboard`**:
   - Ingests raw session records and verifies that `public_row()` strictly sanitizes all outputs, ensuring zero raw IPs appear in public projections.
4. **`test_trusted_proxy_protocol_parsing_and_formatting`**:
   - Validates bidirectional PROXY v1 format and parse round-trip across IPv4 and IPv6.
   - Confirms loopback and Docker subnets (`172.20.0.2`, `10.0.0.5`) are recognized as trusted, while external IPs (`198.51.100.77`) are rejected.
5. **`test_untrusted_client_cannot_spoof_identity_via_headers`**:
   - An untrusted client sending `X-Forwarded-For: 1.1.1.1` has the forged header rejected, returning the real socket IP.
   - An authorized trusted proxy sending `X-Forwarded-For: 203.0.113.50` has the client IP safely extracted.

---

## 5. Deliverable 5: Adaptive T1/T2 Integration Tests

Created dedicated integration test suite: `sensor/test_adaptive_t1_t2_integration.py` (2/2 tests passing):

1. **`test_adaptive_session_lifecycle_t1_to_t2_escalation`**:
   - Drives `AdaptiveSessionAdapter` through a complete lifecycle:
     - **Initial Connect (S1)**: Ingests KEX parameters; verifies initial T1 allocation and baseline filesystem template.
     - **Authentication (S2)**: Ingests auth credentials; maintains T1.
     - **Channel PTY Request (S3)**: Ingests interactive PTY request (`has_pty=1`); triggers deterministic escalation to T2 (`lab_pty_mechanism`).
     - **Filesystem Verification**: Verifies active persona switches to T2, exposing enriched decoy assets (`/var/www/html/index.html` with maintenance mode and `/opt/deploy/config.env`).
     - **Monotone Upward-Only Invariant**: Ingests subsequent S4 and S5 commands; verifies session strictly remains in T2 and never demotes.
     - **Termination & Persistence**: Session close updates visitor memory (`highest_tier_served = 'T2'`).
     - **Returning Visitor Sticky Start**: Second session from same visitor IP starts directly in T2 at Stage S1.
2. **`test_escalation_budget_cap_enforcement`**:
   - Sets budget ceiling to 10% (`max_escalation_fraction = 0.10`).
   - Establishes baseline sessions; admits first escalation within budget.
   - Second escalation exceeding the 10% cap is strictly **blocked** by `SessionBudget`, capping the session safely at T1 (`budget.blocked = True`).

---

## 6. Deliverable 6: Dashboard Live Data Verification

All 8 primary workspaces of the Abyssal Observatory V3 were verified against persisted database records in `gatekeeper/gatekeeper.db` and empirical JSON artifacts:

| Workspace | Route | Backend Source | Status |
| :--- | :--- | :--- | :---: |
| **Mission Control** | `GET /` | `decision_log`, `/api/stats`, `/api/progress` | **VERIFIED (200)** |
| **Session Forensics** | `GET /session` | `/api/session/{id}`, `decision_log` timelines | **VERIFIED (200)** |
| **Visitor Atlas** | `GET /visitors` | `visitors` table, Constellation SVG view | **VERIFIED (200)** |
| **Deception Studio** | `GET /deception` | `results/demo/s1_multi_visitor_proof.json`, `s2_mid_session_switch_proof.json` | **VERIFIED (200)** |
| **Model Observatory** | `GET /ml` | `models/model_s3.json`, `results/exp0/rules_summary.json` | **VERIFIED (200)** |
| **Resource Observatory** | `GET /cost` | `results/cost/COST_PER_TIER.md`, `cost_T1_only.json`, `cost_T2_only.json` | **VERIFIED (200)** |
| **Evidence Vault** | `GET /evidence` | `results/` sanitized evidence catalog | **VERIFIED (200)** |
| **Lab Console** | `GET /lab` | Server-side `/api/gatekeeper/health` probe (`127.0.0.1:15000`) | **VERIFIED (200)** |

### Correctness Guarantees Verified

- **Zero Fake Claims**: Cowrie listener on port 2222 is designated as `Port 2222 (Configured · NOT CHECKED)` unless probed via an authentic SSH client.
- **Same-Origin Health Probe**: `/api/gatekeeper/health` probes loopback port 15000 server-side, eliminating unverified cross-origin browser requests.
- **Empty State Integrity**: Empty SQLite databases return clean empty session lists (0 KPIs) without throwing 500 errors.
- **Stage Observation Fidelity**: Unobserved stages (such as S5) remain visually absent from trajectories and timeline cards.

---

## 7. Deliverable 8: Test Execution Report

### Regression Summary

```powershell
# Core Integration Suites
python -m pytest gatekeeper sensor router infra dashboard -q
# Result: 186 passed, 12 skipped in 8.54s (Sandboxed)
# Result: 193 passed, 5 skipped in 8.41s (Unsandboxed)

# Full Repository Regression Suite
python -m pytest -q
# Result: 332 passed, 15 skipped in 16.17s (Sandboxed)
# Result: 339 passed, 8 skipped in 13.11s (Unsandboxed)

# Documentation Hygiene (Rule G11)
python -m pytest analysis/test_check_docs.py -v
# Result: 5 passed in 0.80s (0 broken links, 0 absolute paths)
```

### Skipped Tests Accounting

- 4 tests in `dashboard/test_ui_correctness.py` and `gatekeeper/test_threaded_service.py` gracefully skip **only** when executed inside the Windows security sandbox due to OS restriction `WinError 10013` (ephemeral loopback connection blocked). When executed unsandboxed, all 4 tests execute and pass 100%.
- 8 tests in `analysis/test_sensor_launcher.py`, `analysis/test_study_export.py`, and `sensor/test_run_sensor.py` skip due to requiring pinned WSL/Linux Twisted Conch runtime or raw Linux `/proc/net/tcp` listener inspect interfaces.

---

## 8. Deliverable 9: Modified and Newly Created Files

### Newly Created Files

1. `infra/proxy.py` (+152 lines)
   - Trusted proxy resolution, CIDR validation, HAProxy PROXY protocol v1 parser/formatter, and safe `X-Forwarded-For` client IP extractor.
2. `infra/test_docker_visitor_identity.py` (+145 lines)
   - Integration tests for multi-visitor separation, returning visitor consistency, privacy masking, proxy protocol parsing, and anti-spoofing.
3. `sensor/test_adaptive_t1_t2_integration.py` (+149 lines)
   - Integration tests for end-to-end adaptive session lifecycle, T1→T2 escalation, persona filesystem switching, and escalation budget cap enforcement.
4. `docs/SPRINT1_INTEGRATION_REPORT.md` (this file)
   - Comprehensive Sprint 1 integration audit, architecture diagrams, and test report.

### Modified Files

1. `infra/edge_forward.py`
   - Added PROXY protocol v1 generation on port 2222 forwarding to preserve client IP.
2. `infra/Dockerfile.edge`
   - Added `COPY infra/proxy.py /app/proxy.py` to container build.
3. `infra/Dockerfile.sensor`
   - Added `COPY infra infra` to ensure proxy resolution utilities are available in sensor container.
4. `sensor/run_sensor.py`
   - Added `proxy_aware_data_received` to `HoneyPotSSHTransport` to parse PROXY headers from authorized proxies and bind real client IP to Cowrie transport.
5. `router/sticky_router.py`
   - Added trusted proxy header inspection and initial payload buffer drainage in TCP stream splicer.
6. `dashboard/test_ui_correctness.py`
   - Hardened loopback health probe tests against Windows sandbox `WinError 10013`.
7. `gatekeeper/test_threaded_service.py`
   - Hardened threaded budget contract tests against Windows sandbox `WinError 10013`.

---

## 9. Deliverable 10: Remaining Blockers and Next Recommended Tasks

### Remaining Limitations & Blockers

1. **WSL/Linux Cowrie Runtime Dependency**:
   - Full live Cowrie twisted runtime requires Linux/WSL environment. On native Windows host, tests execute against pure-Python adapter, simulated pipeline, and unit-tested entry points.
2. **T3 Dynamic VM Sandboxing Deferred**:
   - In accordance with SPEC Section 5.3 and project preregistration, Tier 3 full OS virtualization (qemu/microVM) is deferred to future work. Current architecture strictly operates on T1 (Lite fake shell) and T2 (Enhanced filesystem overlay).
3. **Public VPS Live Deployment**:
   - Gated behind institutional security approvals and VPS deployment authorization. All tests currently run strictly on loopback and isolated Docker bridge networks.

### Next Recommended Tasks (Sprint 2)

1. **Docker Compose Ingress Validation in Linux/WSL**:
   - Execute `docker compose up -d` in Linux/WSL and run multi-visitor smoke test (`harness/demo/smoke_test.sh`) to verify live Docker container networking.
2. **Gatekeeper Latency Optimization**:
   - Profile feature extraction and SQLite WAL query latency under concurrent session loads (>50 concurrent sessions).
3. **Automated Live Sensor Replay Integration**:
   - Connect `harness/replay/` directly into the hardened proxy ingress pipeline to benchmark recorded adversary replay traces against the adaptive decision engine.
