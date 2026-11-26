# H4 result
INCONCLUSIVE. Deep detector runs NOT RUN. No overall scores, category observations or residual signals measured. Handshake-only traffic cannot distinguish the authenticated T1/T2 personas. T3 is unimplemented.

## 2026-11-27 — Authenticated persona comparison

H4 remains INCONCLUSIVE. Docker responded, but the dashboard port was occupied at preflight. Fresh-state T1/T2 runs and T3 were NOT RUN. No detector scores or residual observations were collected in this check.

The isolated installation reports `--deep` (“Run advanced probes: shell semantics, OS coherence,”) and `--safe-mode` (“Handshake-only probes; disables --deep shell/path/auth”). Its help lists no SSH username, password or private-key option for selecting a controlled account. This establishes a CLI limitation. It does not establish that the detector performs no authentication internally. The protocol documents the separate limitation on assigning its connections to a persona (docs/DETECTOR_PROTOCOL.md).

Repeat the prerequisite checks with `docker version`, `Get-NetTCPConnection -State Listen -LocalPort 8080` and, inside the isolated detector environment, `honeypot-auditor --help`.
