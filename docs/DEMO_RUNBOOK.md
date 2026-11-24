# Native WSL demo · LAB_DEMO_NOT_ML

Use a WSL-native checkout with the project's Cowrie environment active. All visitors are scripted lab clients.

| Minutes | Action |
|---|---|
| 0–2 | From the repo root run `bash harness/demo/start_live_demo.sh`. Save its DEMO_DIR and printed stop command. Open http://127.0.0.1:8080 and show the LAB_DEMO warning. |
| 2–4 | Run the printed bot_like command. Read the observed T1 stage chips. |
| 4–6 | Run interactive from the second loopback address. Inspect the PTY-triggered stage and policy badge. |
| 6–8 | Run slow_recon and follow decisions for the same session. Show the declared command-count transition if recorded. |
| 8–10 | Repeat interactive from the same address. Show the returning visitor badge and run the printed stop command. |

| Symptom | Action |
|---|---|
| Occupied port | Identify the owner with `ss -ltnp`. Retry when all three ports are free. |
| Startup times out | Inspect the named log in DEMO_DIR. Verify the active Python environment includes the pinned Cowrie installation. |
| Empty dashboard | Run one printed client command, then check the gatekeeper and sensor logs and the dashboard's database path. |
| Expected transition absent | Show the stored decisions and report the discrepancy. |

**Claim limits.** This demonstration shows declared lab rules and simulated visitors. ML validation, monetary savings, superiority over other tools and a 200 ms deadline guarantee are unsupported. The dashboard reports engine compute time.
