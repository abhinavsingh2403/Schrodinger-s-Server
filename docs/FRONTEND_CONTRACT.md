# Dashboard Front-End Contract: Abyssal Observatory Specification
**Project:** Schrödinger's Server — Adaptive SSH Deception Research Platform  
**Updated:** November 2026 (Version 2.0)  

Start from the repository root with `python -m dashboard.app --db gatekeeper/gatekeeper.db --mode LAB`. Supply the actual decision database to inspect recorded sessions. The listener accepts only IPv4 loopback (`127.0.0.1`). All routes below are GET, read-only and send `Cache-Control: no-store`. Render all text as text (including Markdown from evidence files). Never inject it as HTML.

---

## 1. Workspaces & Data Contract

| Workspace | Route | Consumed Data & Endpoints | Required Scientific Interpretation & Boundary Constraints |
|---|---|---|---|
| **Mission Control** | `/` | `/api/sessions`<br>`/api/decisions/summary` | Live operational posture. Label as "Recorded SSH Sessions" (not "attacks"). When `has_lab_demo` is true, sticky warning banner MUST display `LAB_DEMO_NOT_ML`. Display median and P95 engine compute latency labeled strictly as isolated engine calculation duration. |
| **Session Forensics** | `/session` | `/api/sessions`<br>`/api/session/{masked_id}` | Ordered vertical stage timeline (S1–S5). Mandatory disclaimer: *"Command-level evidence not available in this view. Recorded decisions reflect Gatekeeper policy engine evaluations only."* Latency labeled *"Engine compute latency, not end-to-end"*. Distinct T1 (`#87C6B9`) vs T2 (`#D6B48D`) badges; mid-session escalation pulse. Supports `?id=ses_...`. |
| **Visitor Atlas** | `/visitors` | `/api/sessions` | Group sessions by masked visitor ID (`vis_...`). Mandatory notice: *"Docker Network Bridge Limitation: All containerized lab honeypot traffic traverses local loopback / bridge network interfaces. Visitor clustering reflects lab session grouping and synthetic or recorded pseudonym masks (`vis_...`), rather than geographically distinct remote IP addresses."* |
| **Deception Studio** | `/deception` | `/api/evidence/s2_mid_session_switch_proof`<br>`/api/evidence/s1_multi_visitor_proof`<br>`/api/evidence/s3_showcase` | SVG architecture process diagram, Persona Comparison Matrix (T1 Lite vs T2 Enhanced vs T3 Sandbox), verified transition proof citations. Explains `LAB_DEMO_NOT_ML` profile as mechanism demonstration, not ML evidence. Explains Gate 0 deferral of T3 full OS virtualization. |
| **Model Observatory** | `/ml` | `/api/evidence/metrics`<br>`/api/evidence/EXPERIMENT1_RESULT`<br>`/api/evidence/NULL_ROOT_CAUSE`<br>`/api/evidence/ROOT_CAUSE` | Mandatory banner: *"NO VALIDATED ML GAIN · EXPERIMENTAL HYPOTHESIS NOT SUPPORTED"*. Validity Inspector explaining S2/S5 ineffectiveness and S4 label-leakage invalidity. Pre-registered stage verdicts table, budget ladders (1%, 5%, 10%, 20%), dynamic SVG recall bar charts with random-reference baseline. |
| **Resource Observatory** | `/cost` | `/api/evidence/COST_PER_TIER`<br>`/api/evidence/cost_T1_only`<br>`/api/evidence/cost_T2_only`<br>`/api/evidence/cost_model`<br>`/api/evidence/concurrency_probe` | Matched final-tier hardware measurements (mean/max CPU & memory), dynamic SVG range-bar chart with unbounded upper scale (removes fixed 20% cap), verbatim limitation paragraph from `COST_PER_TIER.md` beginning *"Matched session count"*, zero financial or rupee savings claims. |
| **Evidence Vault** | `/evidence` | `/api/evidence/index`<br>`/api/evidence/{key}`<br>`/api/progress` | Allowlisted research evidence browser, keyword search, status filter chips, active kind filter chips (`All`, `JSON`, `Markdown`), sorting, detail drawer with preformatted Markdown viewer, collapsible JSON tree, copy buttons for paths and raw data. |
| **Lab Console** | `/lab` | `/api/progress`<br>`/api/evidence/safety_check`<br>`/api/sessions` | Local system topology table (Cowrie sensor, Gatekeeper engine, SQLite audit store, Verification dashboard), honest safety check results (preserving `FAIL` on `0.0.0.0` IPv4 listening binding with remediation notes), project engineering progress checklist, demo runbook reference. |
| **Research Archive** | `/research` | Legacy JSON endpoints | Preserved historical dashboard interface with backward compatibility for legacy queries and test coverage. Demoted from primary navigation. |

---

## 2. Forbidden Claims & Anti-Hallucination Invariants

The frontend MUST NEVER output or display:
1. Affirmative claims of ML performance ("ML works", "validated model", "accurate predictions").
2. Financial savings or currency metrics ("cost savings", "saves money", "₹", "rupee", "$").
3. Attack filtering claims ("reduces load", "blocks attacks", "filters attacks", "real attackers").
4. Fabricated safety passes ("safety PASS" when safety check failed).
5. Unmasked IP addresses, private keys, secrets, or raw shell command input text.
6. Hand-typed or fallback measurements: every number must originate directly from an API response; missing data must read `NO DATA` or `NOT RUN`.

---

## 3. Definition of Done for Each Workspace

- [x] Reads only its designated endpoints and preserves source caveats.
- [x] Displays scope, profile, demo label where applicable, status and source.
- [x] Handles unavailable, empty and null values explicitly without uncaught runtime errors.
- [x] All figures come directly from an API response; no hardcoded numerical literals.
- [x] Exercises populated and unavailable responses cleanly.
- [x] Full keyboard accessibility (`:focus-visible`), responsive scaling down to 360px mobile width, and `@media (prefers-reduced-motion: reduce)` support.

GET /replay and /detector render labelled evidence via the existing item API. Visitors reads session groups, Deception reads demo proof items, and Lab reads progress, safety evidence, session availability and same-origin gatekeeper health. The health aliases accept no request-supplied target. Configure the local target with --gatekeeper-host and --gatekeeper-port. Container loopback refers to the dashboard container; a separate gatekeeper can therefore appear UNAVAILABLE. UNKNOWN denotes a refused or unverified target.
Default identifier masking uses unsalted SHA-256. The default has no secret and permits matching the same input across runs. DASHBOARD_MASKING_SALT is optional. Static file service is outside this contract.
