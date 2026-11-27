# Frontend claims audit
Locations refer to the reviewed base commit 3a1fa9d under dashboard/templates.

| File:line | Statement reviewed | Repository evidence | Verdict | Action |
|---|---|---|---|---|
| page_shell.html:1275 | S3 runs a tree | models/model_s3.json model_type | FALSE | Corrected to logistic regression |
| page_shell.html:1269 | R7 runs a trained tree | gatekeeper/decision_api.py score_features | FALSE | Identified constant branch |
| page_shell.html:1266 | Rule names establish operator identity, timing or intent | gatekeeper/decision_api.py score_features | UNVERIFIABLE | Use recorded names |
| page_shell.html:791 | Experiment 1 was preregistered | results/exp1/EXPERIMENT1_RESULT.md | FALSE | Display report |
| page_shell.html:810 | Fixed stage outcomes and causes | results/exp1/metrics.json and ROOT_CAUSE.md | FALSE | Display recorded verdicts and source text |
| page_shell.html:827 | Interval is Bayesian | results/exp1/metrics.json | UNVERIFIABLE | Use reported interval |
| page_shell.html:960 | Missing recall is zero | results/exp1/metrics.json | FALSE | Display native metrics |
| page_shell.html:1253 and index.html:369 | Real VM tier available for inspection | results/detector/DETECTOR_RESULT.md | FALSE | Removed |
| page_shell.html:1616 | Every displayed visitor came through Docker | dashboard/app.py get_sessions_data | UNVERIFIABLE | Removed |
| page_shell.html:1981 | Per-persona resource costs and VM specifications | results/cost/COST_PER_TIER.md | FALSE | Removed matrix |
| page_shell.html:2066 | Current runtime is Windows or WSL | dashboard/app.py | UNVERIFIABLE | Removed |
| page_shell.html:2098 | HTTP success establishes DB availability | dashboard/app.py get_sessions_data | FALSE | Check payload status |
| live.html:541 | Dashboard listener is loopback | dashboard/app.py start | TRUE | Retained |
| page_shell.html:1041 | Root cause report available | results/exp1/ROOT_CAUSE.md | TRUE | Retained evidence view |
| live.html | A cheap gatekeeper decides from initial events which sessions receive higher-fidelity deception | SPEC.md:24 | TRUE | Retained as mission takeaway |
| page_shell.html | Individual session progression reveals the exact moment and mechanism of tier escalation | SPEC.md:24, results/cost/COST_PER_TIER.md:3 | TRUE | Retained as session takeaway |
| page_shell.html | Visitor memory tracks past interactions across sessions while Docker bridge limitations merge lab identities | docs/FRONTEND_CONTRACT.md:15 | TRUE | Retained as visitor takeaway |
| page_shell.html | In-process session adaptation switches personas dynamically between T1 Lite and T2 Hardened | README.md:128, SPEC.md:4 | TRUE | Retained as deception takeaway |
| page_shell.html | Rigorous empirical evaluation against null controls showed no validated ML gain over simple baselines | SPEC.md:26, results/exp1/EXPERIMENT1_RESULT.md | TRUE | Retained as model takeaway |
| page_shell.html | Matched session count and pacing window... cannot isolate a persona-only resource effect | results/cost/COST_PER_TIER.md:74 | TRUE | Retained verbatim limitation |
| page_shell.html | Docker Network Bridge Limitation | docs/FRONTEND_CONTRACT.md:15 | TRUE | Retained verbatim limitation |
| live.html and page_shell.html | Engine compute latency, not end-to-end | docs/FRONTEND_CONTRACT.md:14 | TRUE | Retained latency label |
| page_shell.html | Fail-cheap rule: On any error, timeout, or missing input, defaults safely to T1 | gatekeeper/decision_api.py:10 | TRUE | Retained rule explanation |
| page_shell.html | T3 is future work: full OS virtualization deferred at Gate 0 | README.md:128 | TRUE | Retained deferred notice |
| page_shell.html | Weighted checklist of project work, not a performance measure | dashboard/evidence.py:81 | TRUE | Retained progress checklist note |
| page_shell.html | What we measured, and what we could not prove | SPEC.md:1, EVAL.md:1 | TRUE | Retained page heading |

