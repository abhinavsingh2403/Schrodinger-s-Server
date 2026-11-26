# Front-end Implementation Notes

## Endpoints Read by Page
- Overview (/): reads `/api/sessions` and `/api/decisions/summary`.
- Evidence Vault (/evidence): reads `/api/evidence/index`, `/api/progress`, and `/api/evidence/{id}`.
- ML Experiments (/ml): reads `/api/evidence/metrics`, `/api/evidence/EXPERIMENT1_RESULT`, `/api/evidence/NULL_ROOT_CAUSE`, and `/api/evidence/ROOT_CAUSE`.
- Cost (/cost): reads `/api/evidence/COST_PER_TIER`, `/api/evidence/cost_T1_only`, `/api/evidence/cost_T2_only`, `/api/evidence/cost_model`, and `/api/evidence/concurrency_probe`.
- Session Timeline (/session): reads `/api/sessions` and `/api/session/{masked_id}`.

## Backend Requests (Not Implemented)
1. Dedicated template dispatching in `dashboard/app.py` for each route rather than unified `page_shell.html`.
2. Static asset endpoint (`/static/*`) to decouple CSS/JS logic from inline template definitions.
3. Server-side filter query parameter in `/api/evidence/index` (e.g., `?status=...`) to reduce payload on client.

## NOT RUN
- NOT RUN live: live sensor hardware benchmark runs. Verified using lab test databases and recorded fixtures.
