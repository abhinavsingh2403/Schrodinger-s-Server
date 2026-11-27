# Frontend Story & Conceptual Foundation

**Project:** Schrödinger's Server — Adaptive SSH Deception Research Platform  
**Specification Reference:** `SPEC.md`, `README.md`, `EVAL.md`, `docs/FRONTEND_CONTRACT.md`  
**Date:** November 2026  

---

## 1. Page Purposes & Takeaways

| Page / Route | One-Line Purpose ("What question this page answers") | One-Line Takeaway |
|---|---|---|
| **Mission Control** (`/`) | What is happening, and is the demo ready? | A cheap gatekeeper decides from initial events which sessions receive higher-fidelity deception. |
| **Session Forensics** (`/session`) | What exactly happened in one session? | Individual session progression reveals the exact moment and mechanism of tier escalation. |
| **Visitor Atlas** (`/visitors`) | What happens when someone returns? | Visitor memory tracks past interactions across sessions while Docker bridge limitations merge lab identities. |
| **Deception Engine** (`/deception`) | How does the technology work? | In-process session adaptation switches personas dynamically between T1 Lite and T2 Hardened. |
| **Model & Research** (`/ml`) | What we measured, and what we could not prove. | Rigorous empirical evaluation against null controls showed no validated ML gain over simple baselines. |
| **Resource Observatory** (`/cost`) | What hardware resources do tiers consume? | Matched Docker measurements show minimal persona divergence under in-process cohabitation. |
| **Evidence Vault** (`/evidence`) | What verified research artifacts support these findings? | Pre-registered results and empirical data files remain accessible for independent inspection. |
| **Lab Console** (`/lab`) | What is the operational status of the local lab components? | Verified loopback probes and progress checklists report transparent component posture. |

---

## 2. Static Sentence-to-Source Mapping Table

Every static explanatory statement in the frontend is grounded in the repository source code and documentation:

| Sentence / Phrase | Repository Source File:Line | Verdict |
|---|---|---|
| "A cost-aware adaptive SSH honeypot: spend expensive deception only where it pays." | `README.md:3` | TRUE |
| "A cheap gatekeeper can decide, from the first few events of a session, which sessions deserve a higher-fidelity (higher-cost) honeypot persona, increasing intelligence yield per rupee compared with fixed-persona honeypots." | `SPEC.md:24` | TRUE |
| "The thesis is a hypothesis to be tested, not a result." | `SPEC.md:26` | TRUE |
| "In Internet-facing SSH honeypots, the overwhelming majority of sessions are one-shot automated scans and credential brute-force probes." | `README.md:15` | TRUE |
| "Twisted Conch Router (AdaptiveSSHSession Adapter) Plan A: in-process hook" | `README.md:128`, `SPEC.md:4` | TRUE |
| "T3 is future work: full OS virtualization deferred at Gate 0." | `README.md:128`, `SPEC.md:0` | TRUE |
| "Both personas run inside one sensor process. A T2-final session can spend early time in T1." | `results/cost/COST_PER_TIER.md:3` | TRUE |
| "Matched session count and pacing window. Sampling includes pauses and early T1 time inside T2-final sessions. Both personas share one sensor process. Terminal allocation also differs, so this cannot isolate a persona-only resource effect." | `results/cost/COST_PER_TIER.md:74` | TRUE |
| "Docker Network Bridge Limitation: All containerized lab honeypot traffic traverses local loopback / bridge network interfaces. Visitor clustering reflects lab session grouping and synthetic or recorded pseudonym masks, rather than geographically distinct remote IP addresses." | `docs/FRONTEND_CONTRACT.md:15` | TRUE |
| "Command-level evidence not available in this view. Recorded decisions reflect Gatekeeper policy engine evaluations only." | `docs/FRONTEND_CONTRACT.md:14` | TRUE |
| "Engine compute latency, not end-to-end" | `docs/FRONTEND_CONTRACT.md:14` | TRUE |
| "Fail-cheap rule: On any error, timeout, or missing input, defaults safely to T1" | `gatekeeper/decision_api.py:10` | TRUE |
| "Weighted checklist of project work, not a performance measure." | `dashboard/evidence.py:81` | TRUE |
| "What we measured, and what we could not prove" | `SPEC.md:1`, `EVAL.md:1` | TRUE |
| "Replay of recorded decisions" | `docs/FRONTEND_CONTRACT.md:31` | TRUE |
| "Illustration" | `docs/FRONTEND_CONTRACT.md:31` | TRUE |

---

## 3. Named Constants and Caps

| Constant Name | Value | Purpose / Rationale |
|---|---|---|
| `MAX_GALAXY_PARTICLES` | `50` | Prevents canvas rendering lag and DOM bloat during multi-session particle replay. |
| `MAX_GRAPH_NODES` | `30` | Bounds SVG constellation complexity to preserve 60fps interaction and mobile legibility. |
| `TIME_BUCKET_MINUTES` | `60` | Aggregation interval for session activity sparklines. |
| `TOUR_STEPS` | `5` | Five sequential steps in the interactive 2-minute demonstration tour. |
| `MAX_EXPERIMENT_ITEMS` | `30` | Maximum entries displayed in the experiment ledger timeline. |
| `MAX_RECENT_SESSIONS` | `50` | Maximum recent session rows loaded for real-time trajectory feeds. |

---

## 4. Backend Requests

The following requests are noted for future backend enhancement (no modifications made outside permitted files):
1. **Static Asset Route (`/static/<path>`)**: `dashboard/app.py` currently serves HTML via inline styles/scripts. Adding an endpoint to serve static assets from `dashboard/static/` would allow decoupling stylesheets.
2. **Recorded Terminal Output in Evidence API**: `results/demo/*proof*.json` currently records exit codes and stage decisions, but does not capture raw stdout/pty output. Adding a sanitized terminal transcript to demo evidence would enable terminal side-by-side comparison in Session Forensics.

---

## 5. Phase H Status

**NOT RUN: waiting for docs/UI_PICKS.md**  
(Implementation of React Bits / Motion primitives deferred until specification is provided).

---

## 6. How to Start and View

Start the dashboard locally on loopback IPv4:
```bash
python -m dashboard.app --db gatekeeper/gatekeeper.db --mode LAB --port 8080
```
Open your browser to:
- Mission Control: `http://127.0.0.1:8080/`
- Session Forensics: `http://127.0.0.1:8080/session`
- Visitor Atlas: `http://127.0.0.1:8080/visitors`
- Deception Engine: `http://127.0.0.1:8080/deception`
- Model & Research: `http://127.0.0.1:8080/ml`
