# Front-end Implementation Notes: Abyssal Observatory
**Branch:** `gemini-frontend`  
**Architecture:** 8 Primary Investigation Workspaces + 1 Secondary Archive  
**Specification Reference:** `docs/FRONTEND_AUDIT.md`, `docs/UI_DESIGN.md`, `docs/FRONTEND_CONTRACT.md`  
**Date:** November 2026  

---

## 1. Workspaces & Endpoints Matrix

| Workspace | Route | Consumed Endpoints | Purpose & Core Interactions | Status |
|---|---|---|---|---|
| **Mission Control** | `/` | `/api/sessions`<br>`/api/decisions/summary` | Live operational posture, 5s ticker, KPI strip (Recorded SSH Sessions, Escalated Sessions, Escalation Ratio, Median Engine Compute Latency), aggregate distribution bars (tier, stage, provenance), tier transition feed, real session stream with deep-links to forensics. | **DONE** |
| **Session Forensics** | `/session` | `/api/sessions`<br>`/api/session/{masked_id}` | 2-column forensic timeline: searchable session selector on left, ordered vertical stage progression (S1–S5) on right. Supports `?id=ses_...` URL query param. Distinct T1 (sea-glass teal) vs T2 (warm brass) styling, escalation step pulse, engine compute latency label, and explicit disclaimer: *"Command-level evidence not available in this view"*. | **DONE** |
| **Visitor Atlas** | `/visitors` | `/api/sessions` | Visitor trajectory clustering by masked ID (`vis_...`), returning visitor identification, stage trajectory progression, associated session lists, and Docker network bridge loopback IP limitation notice. Supports `?id=vis_...`. | **DONE** |
| **Deception Studio** | `/deception` | `/api/evidence/s2_mid_session_switch_proof`<br>`/api/evidence/s1_multi_visitor_proof`<br>`/api/evidence/s3_showcase` | SVG architecture pipeline flow diagram, Persona Comparison Matrix (T1 vs T2 vs T3), verified mid-session transition proof citations, explanation of `LAB_DEMO_NOT_ML`, deferred T3 notice. | **DONE** |
| **Model Observatory** | `/ml` | `/api/evidence/metrics`<br>`/api/evidence/EXPERIMENT1_RESULT`<br>`/api/evidence/NULL_ROOT_CAUSE`<br>`/api/evidence/ROOT_CAUSE` | Mandatory banner: *"NO VALIDATED ML GAIN"*. Validity Inspector explaining S2/S5 ineffectiveness and S4 label-leakage invalidity. Pre-registered stage verdicts table, budget ladders (1%, 5%, 10%, 20%), dynamic SVG recall bar charts with random-reference baseline, diagnostic root cause reports. | **DONE** |
| **Resource Observatory** | `/cost` | `/api/evidence/COST_PER_TIER`<br>`/api/evidence/cost_T1_only`<br>`/api/evidence/cost_T2_only`<br>`/api/evidence/cost_model`<br>`/api/evidence/concurrency_probe` | Matched final-tier hardware measurements (mean/max CPU & memory), dynamic SVG range-bar chart with unbounded upper scale (removes fixed 20% cap), verbatim limitation paragraph from `COST_PER_TIER.md`, zero financial/rupee savings claims. | **DONE** |
| **Evidence Vault** | `/evidence` | `/api/evidence/index`<br>`/api/evidence/{key}`<br>`/api/progress` | Allowlisted research evidence browser, keyword search, status filter chips (`All`, `done`, `exploratory`, `NOT RUN`, `INVALID`, `INCONCLUSIVE`), active kind filter chips (`All`, `JSON`, `Markdown`), sorting, detail drawer with preformatted Markdown viewer, collapsible JSON tree, copy buttons for paths and raw data. | **DONE** |
| **Lab Console** | `/lab` | `/api/progress`<br>`/api/evidence/safety_check`<br>`/api/sessions` | Local WSL2/Windows system topology table, honest safety check results (preserving `FAIL` on `0.0.0.0` IPv4 listening binding with remediation notes), project engineering progress checklist, demo runbook reference. | **DONE** |
| **Research Archive** | `/research` | Legacy JSON endpoints | Preserved historical dashboard interface with backward compatibility for legacy queries and test coverage. Demoted from primary navigation. | **DONE** |

---

## 2. Minimal Backend Projections

To route the new workspaces while preserving backend isolation:
- Updated `PAGE_TITLES` dictionary in `dashboard/app.py`:
  ```python
  PAGE_TITLES = {
      "/evidence": "Evidence Vault",
      "/cost": "Resource Observatory",
      "/ml": "Model Observatory",
      "/session": "Session Forensics",
      "/visitors": "Visitor Atlas",
      "/deception": "Deception Studio",
      "/lab": "Lab Console",
  }
  ```
- All new routes seamlessly render through `dashboard/templates/page_shell.html` with title substitution and client-side boot dispatching.
- No existing API route contracts or database schemas were modified or broken.

---

## 3. Anti-Hallucination & Security Guards

1. **Zero External Network Dependencies:** No CDNs (Tailwind CDN completely eliminated), no Google Fonts, no external scripts. Runs 100% offline on loopback (`127.0.0.1`).
2. **Zero Injected Data via `innerHTML`:** All text and telemetry are injected strictly via `document.createElement` and `textContent`.
3. **No Fabricated Metrics:** Missing data strictly displays `NO DATA` or `NOT RUN`.
4. **Honest Scientific Evaluation:**
   - Negative and inconclusive results styled in neutral warning tones (`#3d2812` / `#fb923c`), never green.
   - Mandatory banner on `/ml`: *"NO VALIDATED ML GAIN · EXPERIMENTAL HYPOTHESIS NOT SUPPORTED"*.
   - Verbatim methodology caveat on `/cost`: Matched session sampling inside shared sensor process cannot isolate persona-only resource impact.
   - Preserved `FAIL` on `/lab` for `0.0.0.0` sensor binding.
5. **Masked Identifiers Only:** All session IDs (`ses_...`) and visitor IDs (`vis_...`) are salted HMAC hashes; no raw IP addresses or credentials appear anywhere.

---

## 4. Verification & Testing

- **Backend / Contract Test Suite:**
  `& ".venv\Scripts\python.exe" -m pytest -q`
  - Total Suite: **324 passed, 4 skipped in 9.73s**
  - Dashboard Suite (`dashboard/`): **68 passed, 1 skipped in 0.92s**
- **Live Local Daemon Server:**
  `python -m dashboard.app --host 127.0.0.1 --port 8080 --mode LAB --db gatekeeper/gatekeeper.db`
  - All 8 workspaces + archive verified returning HTTP 200 on loopback.
- **Browser Visual Verification:**
  - Browser subagent executed across all 8 workspaces on `http://127.0.0.1:8080/`.
  - Visual hierarchy, contrast, responsive grids, and interactive inspection drawers confirmed.
