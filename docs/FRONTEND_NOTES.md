# Front-end Implementation Notes

## Endpoints Read by Page
- Overview (/): reads `/api/sessions` and `/api/decisions/summary`.
- Evidence Vault (/evidence): reads `/api/evidence/index`, `/api/progress`, and `/api/evidence/{id}`.
- ML Experiments (/ml): reads `/api/evidence/metrics`, `/api/evidence/EXPERIMENT1_RESULT`, `/api/evidence/NULL_ROOT_CAUSE`, and `/api/evidence/ROOT_CAUSE`.
- Cost (/cost): reads `/api/evidence/COST_PER_TIER`, `/api/evidence/cost_T1_only`, `/api/evidence/cost_T2_only`, `/api/evidence/cost_model`, and `/api/evidence/concurrency_probe`.
- Session Timeline (/session): reads `/api/sessions` and `/api/session/{masked_id}`.
- Research Archive (/research): reads `/api/stats`, `/api/arms`, and `/api/decisions`.

## How to Start and View
`python -m dashboard.app --db gatekeeper/gatekeeper.db --mode LAB --port 8080`
Open `http://127.0.0.1:8080/` in browser. Works offline on loopback without external network.

## Backend Requests (Not Implemented)
1. Dedicated routes and template dispatching in `dashboard/app.py` for `/replay` and `/detector` endpoints.
2. Static asset endpoint (`/static/*`) in `dashboard/app.py` to allow splitting CSS/JS from HTML.
3. Server-side filter query parameters in `/api/evidence/index` (e.g. `?status=done`) to avoid full index download.

## NOT RUN
- Phase 4: NOT RUN: waiting for docs/UI_PICKS.md (file absent).
- Visual check: visual check NOT RUN (Chromium/Playwright not installed on local host).
- Live runs: live sensor daemon hardware benchmark runs. Verified via loopback smoke test and pytest suite.
