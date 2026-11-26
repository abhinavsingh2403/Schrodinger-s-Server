# Dashboard front-end contract

Start from the repository root with `python -m dashboard.app --db gatekeeper/gatekeeper.db`. Supply the actual decision database to see sessions. The listener accepts only IPv4 loopback. All routes below are GET, read-only and send `Cache-Control: no-store`. Render text as text (including Markdown from evidence files). Never inject it as HTML.

## Data and examples

Each linked JSON example is the actual public response in the fixture's `response` field. The wrapper records the route, HTTP status, generator and source revision. Regenerate with `python -m dashboard.make_fixtures`. Decision examples come from a temporary lab database populated by the decision engine. They illustrate a mechanism. Do not poll fixtures as live evidence.

| Route | Successful shape and example | Empty or unavailable |
|---|---|---|
| / and /index.html | Session dashboard HTML, [template](../dashboard/templates/live.html) | Same page with empty sessions |
| /research | Research HTML, [template](../dashboard/templates/index.html) | Same page with panel-level availability |
| /api/evidence/index | Labels, items with ID, title, kind, source, labels and available top-level fields. [Index](../dashboard/fixtures/index.json) | HTTP 200, empty items and explanation |
| /api/evidence/{id} | Labels, ID, title, kind, data. JSON keeps native object or array shape. Markdown has data.text. [JSON](../dashboard/fixtures/evidence_metrics.json) · [Markdown](../dashboard/fixtures/evidence_COST_PER_TIER.json) | HTTP 404, labels, null data and empty explanation for unknown, missing, oversized or unreadable item |
| /api/progress | Same envelope, data with percentage, earned, total, items and an explanatory note. [Checklist](../dashboard/fixtures/progress.json) | Same unavailable-file shape |
| /api/decisions/summary | Labels, data with total_sessions, counts grouped by tier, stage, provenance, policy_profile and score_source. Latency in milliseconds has min, median, nearest-rank p95 and max over non-null observations. [Summary](../dashboard/fixtures/summary.json) | [Empty summary](../dashboard/fixtures/empty_summary.json), HTTP 200. Null latency when no timings exist |
| /api/session/{masked_id} | Labels, data.session_id and decisions in database insertion order, earliest first. Each has stage, tier_decided, score, score_source, latency_ms, timestamp, provenance, policy_profile and demo_label. Take the complete masked ID from /api/sessions. [Timeline](../dashboard/fixtures/session.json) | [Unknown session](../dashboard/fixtures/unknown_session.json), HTTP 404 |
| /api/sessions | sessions with masked identifiers, stages, transitions and decisions, returning_visitor and reached_t2; kpis, has_lab_demo. [Sessions](../dashboard/fixtures/sessions.json) | Empty sessions, null fraction and median |
| /api/decisions | Recent decisions newest first, masked identifiers, source, profile. [Decisions](../dashboard/fixtures/decisions.json) | Empty decisions |
| /api/stats | Recorded dataset and sensor aggregates. [Stats](../dashboard/fixtures/stats.json) | NO DATA when base rates unavailable |
| /api/arms | Recorded arm objects, simulation methodology and disclaimer. [Arms](../dashboard/fixtures/arms.json) | NO DATA |
| /api/model | Serialized model metadata. [Model](../dashboard/fixtures/model.json) | NO DATA |
| /api/exp0 | Mechanical gate, counts and stage results. [Experiment](../dashboard/fixtures/exp0.json) | NO DATA |
| /api/natural_experiment | Recorded instance data, association and caveats. [Association](../dashboard/fixtures/natural_experiment.json) | NO DATA |
| /api/detector | Recorded detector data or availability notice. [Detector](../dashboard/fixtures/detector.json) | NO DATA and notice |

The legacy JSON routes (sessions through detector in the table) preserve their status and source fields and add the common labels under `metadata`. Legacy unavailable responses use HTTP 200. New routes carry labels at the top level. Unknown API routes return HTTP 404 with null data and an explanation. No event-log endpoint is enabled.

Scope is LAB, LIVE, SYNTHETIC or UNKNOWN. Profile is DEFAULT, LAB_DEMO or UNKNOWN. Mixed or absent labels map to UNKNOWN at envelope level. Keep individual decision labels visible. LAB_DEMO carries LAB_DEMO_NOT_ML. Status is done, exploratory, NOT RUN, INVALID or INCONCLUSIVE. Source names are repository-relative or the logical decision_log table. For the catalog, source identifies the catalog definition. Document status is an editorial classification maintained beside its exact filename in dashboard/evidence.py. Never convert the document status into a stage verdict. Display the stored stage verdicts in metrics.json verbatim.

The index is the complete public allowlist. Only IDs from it resolve, with a two-MiB read limit per file. Source commands, identifiers, command outputs and sensitive fields may be withheld. Markdown remains text. No numeric extraction from Markdown. The weighted checklist measures project work.

## Pages and the only data each may show

| Page | Data | Required interpretation |
|---|---|---|
| Evidence Vault | Evidence index and item routes | Show filename, scope, status and profile beside the evidence |
| Cost | Cost evidence items and COST_PER_TIER Markdown | Show the limitation paragraph beginning “Matched session count” verbatim from the endpoint. Keep it beside CPU and memory results |
| ML Experiments | Experiment 1 metrics and Experiment 0 verdict Markdown | Show INVALID and INCONCLUSIVE as returned. Required banner “No validated ML gain” |
| Session Timeline | Masked sessions and their ordered decision rows | Only recorded decisions. Label latency as engine compute time, not end-to-end |
| Overview | Decision summary and progress | Keep the checklist and measured operational counts distinct |

## Do not show

Exclude affirmative ML-performance badges, financial savings or rupee figures, load-reduction or attack-blocking claims, claims about actual attackers, an overall safety pass, unmasked identifiers and session feature vectors or thresholds. The latter are absent from the decision log. Legacy research routes are outside the new pages' data contract.

## Definition of done for a page

- [ ] Reads only its designated endpoints and preserves source caveats.
- [ ] Displays scope, profile, demo label where applicable, status and source.
- [ ] Handles unavailable, empty and null values explicitly.
- [ ] All figures come from a response; no fallback measurements.
- [ ] Exercises populated and unavailable fixture responses.

GET /evidence, /cost, /ml and /session return the [page shell](../dashboard/templates/page_shell.html) with the corresponding title, navigation, visible UNKNOWN scope/profile and NO DATA until a renderer loads evidence. HTML routes return HTTP 404 for unknown pages.
