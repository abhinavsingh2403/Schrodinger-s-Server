# Frontend Code Audit & Architectural Evaluation Report
**Project:** Schrödinger's Server — Adaptive SSH Deception Research Platform  
**Target:** Frontend Refactoring on branch `gemini-frontend`  
**Date:** November 2026  
**Auditor:** Antigravity Autonomous Agent (DeepMind)  

---

## 1. Executive Summary

A comprehensive source-level and architectural audit of the Schrödinger's Server frontend was conducted against the research codebase, backend routes, data contracts, and experimental artifacts.

The current system has a solid functional baseline (offline loopback capability, strictly typed JSON endpoints, no external runtime dependencies). However, it initially operated as disjoint utility screens rather than a cohesive **cybersecurity investigation and scientific defense platform**.

### Core Ratings & Target
- **Initial Source-Level Rating:** 7.5 / 10
- **Target Post-Implementation Rating:** 9.0–9.5 / 10 (conditional on full browser verification, zero-hallucination fidelity, and evidence traceability)

---

## 2. Route & Endpoint Audit Matrix

| Route | Primary Template | Consumed Endpoints | Current Status & Gaps | Required Architectural Transformation |
|---|---|---|---|---|
| `/` | `live.html` | `/api/sessions`<br>`/api/decisions/summary` | Labeled "Recorded Attacks" instead of "Recorded SSH Sessions". Basic session table without rapid stage filter or prominent transition stream. | **Mission Control**: Live operational posture, live 5s polling ticker, KPI strip, tier escalation monitor, real session stream with clickable deep-links into forensics. |
| `/session` | `page_shell.html` | `/api/sessions`<br>`/api/session/{masked_id}` | Decision list exists but lacks clear stage-to-stage visual hierarchy. Latency was not explicitly distinguished from end-to-end network time. | **Session Forensics**: 2-column layout. Searchable sessions on left, ordered vertical stage timeline (S1–S5) on right. Clear T1 (Sea-glass teal) vs T2 (Warm brass) styling, transition markers, explicit latency caveat (*"engine compute time, not end-to-end"*), and explicit notice: *"Command-level evidence not available in this view"*. |
| `/visitors` | *New* | `/api/sessions` | Previously missing. Visitors could only be seen nested inside individual sessions. | **Visitor Atlas**: Masked visitor clustering (`vis_...`), returning visitor identification, session counts, stage progression distribution, and Docker network bridge loopback IP limitation notice. |
| `/deception` | *New* | `/api/evidence/s2_mid_session_switch_proof`<br>`/api/evidence/s1_multi_visitor_proof`<br>`/api/evidence/s3_showcase` | Previously missing. No visual comparison between T1 and T2 deception environments. | **Deception Studio**: Persona comparison (T1 fake shell vs T2 enhanced shell), SVG architecture pipeline diagram, verified transition proof citations, `LAB_DEMO_NOT_ML` explanation, deferred T3 notice. |
| `/ml` | `page_shell.html` | `/api/evidence/metrics`<br>`/api/evidence/EXPERIMENT1_RESULT`<br>`/api/evidence/NULL_ROOT_CAUSE`<br>`/api/evidence/ROOT_CAUSE` | Good raw data, but high S4 recall bar could mislead examiners into thinking ML succeeded. | **Model Observatory**: Exp 0 vs Exp 1 toggle, stage selector (S2, S4, S5), budget ladders, dynamic SVG charts with random-reference baseline, validity inspector explaining `INVALID` and `INCONCLUSIVE` verdicts, mandatory banner: *"NO VALIDATED ML GAIN"*. |
| `/cost` | `page_shell.html` | `/api/evidence/COST_PER_TIER`<br>`/api/evidence/index` | Fixed CPU chart cap at 20% clipped higher readings. Wording implied isolated server runs rather than persona shifts within shared process. | **Resource Observatory**: Dynamic SVG chart scaling, repeat-spread range bars, matched final-tier lab measurements (mean/max CPU & memory), verbatim limitation paragraph from `COST_PER_TIER.md`, zero financial/rupee savings claims. |
| `/evidence` | `page_shell.html` | `/api/evidence/index`<br>`/api/evidence/{key}`<br>`/api/progress` | Search and sort worked, but `activeKindFilter` was an unreferenced variable in JS. Missing visual file-kind toggle chips. | **Evidence Vault**: Allowlisted evidence browser, search, active kind filter (`All`, `JSON`, `Markdown`), sort, detail drawer with preformatted Markdown, collapsible JSON tree, copy buttons for paths and raw data. |
| `/lab` | *New* | `/api/progress`<br>`/api/evidence/safety_check`<br>`/api/sessions` | Missing overview of local WSL lab infrastructure and safety boundaries. | **Lab Console**: Read-only topology (Cowrie, Gatekeeper, SQLite DB, Dashboard), demo runbook guide, honest display of safety check results (`FAIL` preserved on IPv4 binding, no fake `PASS`), known research boundaries. |
| `/research` | `index.html` | Legacy JSON endpoints | Redundant legacy layout duplicating overview metrics. | **Research Archive**: Demoted from primary navigation; preserved for backward compatibility and test coverage. |

---

## 3. Specific Empirical Findings & Gaps

### 3.1 Session Forensics Data Reality
- `/api/session/{masked_id}` provides:
  - `session_id`, `visitor_id`, `returning_visitor`
  - Array of decisions: `stage`, `tier`, `score`, `score_source`, `provenance`, `policy_profile`, `latency_ms`, `timestamp`
- **Data Gap:** The gatekeeper SQLite database does **not** persist full command text strings or raw input streams due to honeypot isolation rules and privacy redaction.
- **Action:** Must explicitly label: *"Command-level evidence not available in this view. Recorded decisions reflect Gatekeeper policy engine evaluations only."* Latency must be explicitly labeled *"Engine compute latency (ms), excluding sensor network transmission"*.

### 3.2 Resource & Concurrency Scaling
- `results/cost/COST_PER_TIER.md` records:
  - T1: Mean CPU 0.05%, Peak 1.95%, Memory Mean 49.11 MB, Max 49.33 MB
  - T2: Mean CPU 0.06%, Peak 2.05%, Memory Mean 49.11 MB, Max 49.38 MB
  - T3: Deferred (`NOT RUN`)
- **Action:** Avoid misleading claims that T1 is "cheaper" or "saves cloud infrastructure budget". Both personas run within the same Python process in Cowrie; memory consumption is identical (~49 MB) and CPU variance is sub-0.02%. Use dynamic chart bounds and include the verbatim limitation text from `COST_PER_TIER.md`.

### 3.3 ML Experiments & Negative Result Integrity
- Pre-registration and Experiment 1 results clearly demonstrate:
  - Gate 0 failed to reject the null hypothesis.
  - S4 model precision was confounded by label definition leakage; S2 and S5 yielded inconclusive discrimination.
  - Verdict is strictly `INVALID` / `INCONCLUSIVE`.
- **Action:** Mandatory prominent warning banner: `NO VALIDATED ML GAIN · EXPERIMENTAL HYPOTHESIS NOT SUPPORTED`. S4 recall numbers must be visually counterbalanced with the validity inspector explaining why raw recall is unrepresentative.

### 3.4 Frontend Purity & Zero AI Slop Directives
1. **No External CDNs or Fonts:** Completely offline on loopback (`127.0.0.1`). Clean system font stacks.
2. **No Data-Driven `innerHTML`:** All text and values rendered safely via `document.createElement`, `textContent`, and DOM nodes.
3. **No Fabricated Data:** If an API endpoint returns empty or fails, display `NO DATA` or `NOT RUN`.
4. **Honest Safety Audits:** The `safety_check.json` contains a `FAIL` on `0.0.0.0` IPv4 listening binding. This must be presented verbatim as `FAIL` with remediation notes, never whitewashed to `PASS`.

---

## 4. Implementation Strategy

1. **Abyssal Observatory Design System:** Standardize palette variables (`#0B141B`, `#14232C`, `#1B2D35`, `#2B4048`, `#87C6B9`, `#D6B48D`, `#D88D81`, `#9A9BCF`) across `page_shell.html` and `live.html`.
2. **Minimal Backend Route Projection:** Add `/visitors`, `/deception`, and `/lab` to `PAGE_TITLES` in `dashboard/app.py`.
3. **Workspace Dispatching in `page_shell.html`:** Implement dedicated renderers for each of the 7 sub-routes.
4. **Mission Control Refactoring in `live.html`:** Refine live polling, terminology ("Recorded SSH Sessions"), and KPI monitors.
5. **Contract & Regression Testing:** Ensure all existing 59 dashboard tests and new workspace tests pass cleanly.
