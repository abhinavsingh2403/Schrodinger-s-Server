# SPEC.md: System Specification

Version 0.2 (2026-11-11, revised after external review). **Status: DRAFT, contingent on Gate 0** (see section 0). Companion documents: `EVAL.md` (how we measure), `DATA.md`, `SPIKES.md`, `SAFETY.md`.
Tags used for facts: **[V]** read directly from the source page; **[S]** seen in a search snippet only; **[U]** unverified assumption that must be checked. Details in `CLAIMS.md`.

---

## 0. Scope and gating (v0.2)

Added after an external review that judged v0.1 too large and its central ML premise untested.

- **MVP = offline dataset study + persona comparison + cost model + dashboard of offline results.** Everything else is gated or deferred (`README.md` section 8).
- **Gate 0 (`EXPERIMENT0.md`, `WEEK1.md`):** before building the gatekeeper, test whether a learned model beats simple rules at early decision stages. The outcome (PASS-ML, PASS-LATE-ONLY, FAIL) selects the scope.
- **Shadow mode** is the default for any live gatekeeper: it logs the decision it *would* make without changing what the visitor sees. Adaptive serving (arm C) is gated.
- Deferred unless gates pass: T3 (5.1), most of the adversary harness beyond the third-party detector and replay (5.4), Model A (7.2), and the live-trial and human-study parts of `EVAL.md`.
- Where this section conflicts with a later section, **section 0 wins**.

---

## 1. Purpose and thesis

Most sessions on an Internet-facing SSH honeypot are one-shot automation; a published deployment recorded 147,752 non-interactive sessions out of 148,850 and 150 interactive ones [S, CLAIMS P2]. Therefore:

> **Thesis.** A cheap gatekeeper can decide, from the first few events of a session, which sessions deserve a higher-fidelity (higher-cost) honeypot persona, increasing *intelligence yield per rupee* compared with fixed-persona honeypots.

The thesis is a hypothesis to be tested, not a result. See `EVAL.md` H1 to H4.

## 2. Goals and non-goals

**Goals**
- G1. Build an SSH honeypot with three cost tiers sharing one machine identity.
- G2. Build a gatekeeper (value model, agent detector, policy) that picks a tier per visitor. (Per section 0: the agent detector is deferred; the live trial is gated.)
- G3. Measure yield, cost and detectability against baselines using offline data, lab adversaries and a live randomized trial. (Lab adversaries and the live trial are gated; the MVP is offline.)
- G4. Produce a reproducible repository where every reported number comes from a script.

**Non-goals**
- Telnet, HTTP or other protocols. SSH only.
- Training or fine-tuning LLMs. Deep reinforcement learning.
- Blockchain features, eBPF, malware reverse engineering, STIX/TAXII export.
- Hack-back, counter-exploitation, or identifying real people.
- Claims about protecting production systems by making them look like honeypots (this is the "fake honeypot" idea of Rowe [S, CLAIMS T9]; out of scope as a claim).

## 3. Definitions

| Term | Meaning |
|---|---|
| Session | One SSH connection as identified by Cowrie's session id |
| Visitor | A source identity (HMAC of source IP with a secret salt; see 5.2) |
| Tier | Fidelity/cost level of the persona: T1 Lite, T2 Hardened, T3 Real |
| Identity profile | Hostname, OS release, kernel string, uptime baseline, user list; **identical across tiers** |
| Stage | A decision point in a session: S0 connect, S1 handshake, S2 auth, S3 session start, S4 first command, S5 first three commands |
| Escalation | Moving a visitor to a higher tier. **Upward only** |
| Value label | Outcome-based label used to train Model V (see 7.1) |
| Yield | Numeric intelligence-gain score of a session (see 9.1) |
| Cost | Measured resource cost of serving a session, in resource units and rupees (see 9.2) |
| Arm | An experimental condition in the live trial (see EVAL 5.6) |

## 4. Architecture

```
                         Internet (attackers, scanners, bots)
                                      |
                              [ VPS firewall ]
                                      |
                     +----------------+-----------------+
                     |                Router            |   Plan A: in-process hook
                     |  (escalation / tier selection)   |   Plan B: sticky TCP splice
                     +--------+---------------+---------+   (decided by SPIKES S1)
                              |               |
                      +-------+--+     +------+-----+      +-----------------+
                      | T1 Lite  |     | T2 Hardened|      | T3 Real VM      |
                      | Cowrie   |     | Cowrie     |      | Cowrie proxy -> |
                      | shell    |     | shell+fs   |      | sandboxed VM    |
                      +-------+--+     +------+-----+      +--------+--------+
                              \               |                     /
                               +---- Cowrie JSON event logs -------+
                                              |
                                   +----------v----------+
                                   |     Gatekeeper      |
                                   | features, Model V,  |
                                   | Model A, policy,    |
                                   | visitor memory      |
                                   +----------+----------+
                                              |
                          +-------------------+-------------------+
                          |                                       |
                  decision log + metrics                    Dashboard (read-only)
```

Separate lab environment (never mixed with the public sensor): Kali-based harness running adversaries against a lab copy of the sensor (see 5.4).

## 5. Components

### 5.1 Sensor (Cowrie)

- Use a **pinned release** of Cowrie. At time of writing PyPI showed 3.1.2, published October 2026 [S]. Re-check at build time and pin the exact version and hash in `sensor/`. Read the changelog for security fixes before pinning, because a 2026 study analysed Cowrie's implementation attack surface including a flaw in affected versions [S, CLAIMS P5].
- Python 3.11+ is listed for recent releases [S]. Verify against the pinned version.
- SSH only; Telnet disabled.
- Logs: Cowrie JSON event log, timestamps in UTC. Relevant events [S, CLAIMS T3]: `cowrie.client.kex` (hassh, hasshAlgorithms, kexAlgs, keyAlgs), `cowrie.client.version`, `cowrie.client.size`, `cowrie.client.var`, `cowrie.login.success/failed`, `cowrie.command.input/failed`, `cowrie.session.params`, `cowrie.session.closed` (duration), `cowrie.session.file_download/file_upload`, `cowrie.direct-tcpip.request/data`. Confirm exact names and attributes against the pinned version.
- **Identity profile** (`sensor/identity.yaml`): one definition of hostname, distro, kernel string, uptime baseline, users. All tiers must conform. T3's VM image dictates the identity (an Ubuntu 18.04 image is shipped with Cowrie's backend pool docs [S]); T1 and T2 are configured to match it. Default Cowrie ships a fake filesystem resembling an old Debian [S], which would contradict a newer Ubuntu image, so T1 cannot be left fully default on the identity axis (see Risk R8).

| Tier | Mechanism | Cost profile | Notes |
|---|---|---|---|
| **T1 Lite** | Cowrie `backend = shell`, near-default behaviour, identity-matched | Lowest | Used for the baseline arm A. Reuse the published "Baseline" configuration from the 160-instance dataset repo for comparability [S; license U, see SPIKES S3] |
| **T2 Hardened** | Cowrie `backend = shell` with a custom fake filesystem (`createfs`/`fsctl` tools [S]), richer file contents, adjusted command outputs, optional per-user persistence | Low to medium | Reuse the published "Enhanced"/persistence configurations where licensing allows |
| **T3 Real** | Cowrie proxy mode to a real sandboxed Linux guest. Preferred: Cowrie's backend pool (QEMU/libvirt) with `[proxy] backend = pool`, `[backend_pool] pool_only = false`, `pool = local` [S] | Highest | No LLM, so no LLM hallucination. Egress must be blocked (network filter) [S]. Proxy-to-pool traffic is unencrypted, keep it local [S] |
| LLM tier | Cowrie's built-in LLM backend is marked experimental [S] | Variable | **Not part of the default system.** Optional lab-only ablation |

**T3 feasibility warning [U].** QEMU/libvirt guests on a cloud VPS need hardware virtualization (nested virtualization) or run very slowly in software emulation. Many VPS plans do not expose `/dev/kvm`. This is checked in SPIKES S2. Fallback ladder for T3: (a) backend pool on a VPS/bare-metal host that exposes KVM; (b) Cowrie proxy mode to a single resettable sandbox container or VM (weaker isolation between visitors, document it); (c) drop T3 and report as future work.

### 5.2 Gatekeeper

Responsibilities: ingest Cowrie events, build stage features, run models, apply policy, remember visitors, expose a decision API, log every decision.

- **Visitor memory.** `visitor_id = HMAC-SHA256(secret_salt, source_ip)`. Store: first_seen, n_sessions, highest_tier_served, last_value_label, last_agent_score. The raw IP is stored only in the sensor's own log. The secret salt is never committed. Dashboard shows masked values only.
- **Storage.** SQLite for the decision log and visitor memory (single VPS, low write rate). Use WAL mode. Back up daily.
- **Fail-cheap rule.** If the gatekeeper is unreachable or errors, serve T1. Never block or drop a connection because of a gatekeeper failure.
- **Latency target.** Decisions at stages S1 to S3 within 50 ms at p95 on the VPS **[target, measure in SPIKES S2]**.

### 5.3 Router / escalation mechanism

Requirement: a visitor sees one consistent machine identity and tiers only escalate upward; never flip between "fake" and "real" personas within a visitor's history.

- **Plan A (preferred): in-process hook** in a fork or plugin of Cowrie that selects the persona (filesystem, command set, backend) when a session reaches a stage. Supports intra-session decisions. Depends on what SPIKES S1 finds in Cowrie's code. Cowrie's documentation describes backends (shell, proxy, pool, LLM) as configuration choices; I did not find per-session switching documented **[U]**.
- **Plan B (fallback): sticky multi-instance routing.** Run one Cowrie instance per tier on different internal ports. A small asyncio TCP front-end accepts connections and splices them to an instance chosen **at accept time** from visitor memory only. It must not touch the SSH byte stream (no banner rewriting). This only supports **cross-session** adaptation (a visitor's later sessions can be escalated) and cannot use handshake or command features for the current session. Document this limitation in results if Plan B is used.
- Decision stage is a parameter. Offline experiments (EVAL 5, Experiment 0) determine which stage is worth using; the live system uses the earliest stage the chosen plan supports.
- **Decision-stage tension (acknowledged).** Before any command (S1 to S3) information is scarce; after commands (S4, S5) information is richer, but acting on it means changing the persona mid-session. The rule "upward-only, same identity" does **not** forbid mid-session escalation; it requires that a later tier looks like the same machine. Whether mid-session escalation is *possible* in Cowrie is unknown until SPIKES S1. If it is not possible, the project either (a) restricts itself to pre-command decisions and cross-session adaptation (Plan B), or (b) reports late-stage results as offline analysis only. Experiment 0 shows which stages carry signal, so we do not build mid-session machinery for a stage that carries none.

### 5.4 Adversary harness (lab only)

Runs in a Kali-based container on a **separate lab network and a separate lab copy of the sensor**. Lab traffic must never enter the public RCT statistics (see SAFETY).

| Adversary | Purpose | Source |
|---|---|---|
| honeypot-auditor (third-party detector) | Independent detectability score. Deep mode covers shell semantics, OS coherence, HASSH, TCP stack, latency and more [S]. Use only against our own targets with its authorization flag [S] | PyPI `honeypot-auditor` (MIT [S]) |
| Trace replay | Replays real botnet command sequences taken from the public dataset against the lab sensor | `harness/replay/` (ours; inputs from DATA D1) |
| LLM agents | Real AI attackers over SSH with at least 4 different open-weight models via Ollama | ARACNE (SSH-driven, GPL-2.0, supports Ollama [S]); PentestGPT (supports local LLM servers; its autonomous mode drives Claude Code or Codex [S]) |
| Human volunteers | Blind "real or honeypot?" test and human-class data | `harness/human_study/` |

Replay and scripted tools are **not** considered independent adversaries when we tune the honeypot to them. Tune on validation traffic, report on held-out adversaries.

### 5.5 Analysis pipeline

- DuckDB (or equivalent) over the dataset files; scripts in `analysis/`. Notebooks are for exploration; every reported number must come from a script that writes into `results/`.
- Stage A uses `session_aggregation.jsonl.gz` (about 1.3 GB). Stage B uses a **subset of days** from `data_all.zip` (about 19.4 GB, 51 daily files) for event-level features such as hassh and timing. See `DATA.md`.

### 5.6 Dashboard (read-only)

Panels:
1. **Collapse board.** Each arriving visitor appears as an undecided box that resolves to T1, T2 or T3 with the top reason features.
2. **Cost meter.** Cumulative cost in resource units and rupees versus an always-T2 and an always-T3 counterfactual (computed, labelled as counterfactual).
3. **Escalation-efficiency curve** and **early-decision curve** from the latest offline run (static images regenerated by script).
4. **Agent detector panel** showing lab agents with a persistent "LAB" banner.
5. **Session replay** (split view: what the visitor saw / what the gatekeeper decided).

Rules: every panel states "LIVE", "LAB" or "RECORDED". IPs are masked. No panel shows a number that is not produced by a script in this repo.

### 5.7 Infra

- One public VPS for the sensor (provider choice is a team decision; check the provider's acceptable-use policy for honeypots **[U]**, see SAFETY).
- Real administrative SSH on a non-default port, key-only, restricted by source allowlist. The honeypot owns the standard SSH port.
- `docker-compose` for sensor tiers and gatekeeper where possible. T3 libvirt guests run on the host.
- Time sync (NTP) on all hosts; logs in UTC.

## 6. Interfaces

### 6.1 Decision API (internal)

`POST /decide`
```json
{
  "visitor_id": "hmac-hex",
  "session_id": "cowrie-session-id",
  "stage": "S3",
  "features": { "...": "stage-specific, see 7.3" },
  "ts_utc": "2026-11-10T12:00:00.000Z"
}
```
Response:
```json
{
  "tier": "T1|T2|T3",
  "reason": ["top feature names"],
  "p_value": 0.0,
  "p_agent": 0.0,
  "policy_version": "p1",
  "model_versions": {"v": "v1", "a": "a1"}
}
```

### 6.2 Decision log table (`decisions`)

`id, ts_utc, visitor_id, session_id, stage, tier_before, tier_after, p_value, p_agent, policy_version, model_v_version, model_a_version, arm, features_json, latency_ms`

### 6.3 Session summary table (`sessions`)

`session_id, visitor_id, arm, tier_final, start_utc, end_utc, n_commands, n_distinct_commands, n_file_transfers, n_pivot_requests, attack_tags_json, value_label, yield, cpu_seconds, gb_seconds, vm_boots, cost_units, cost_inr, lab_flag`

`lab_flag = 1` rows are excluded from every live-trial statistic.

## 7. Models

### 7.1 Model V: value gatekeeper

- **Prediction target (label), proposed, frozen before training (EVAL 2):**
  `value = 1` if the session has at least one of: (a) at least N_CMD distinct commands (default N_CMD = 5), (b) at least one file download or upload, (c) at least one direct-tcpip (port-forward/pivot) request. Otherwise 0.
- **Label window (leakage rule).** For a decision at stage k, the evaluation set excludes sessions whose *prefix up to stage k* already satisfies the label (for example, a file download in the first command). Sessions that never reach stage k are not in that stage's evaluation set; report the reach rate per stage.
- **Triviality warning.** After the first command, predicting continued interaction is easy. The real scientific question is whether a learned model beats simple rules *before any command* (S1 to S3). This is tested first (Experiment 0).
- Labels come from observed outcomes, not human labeling. The labels depend on which persona served the session (a session that was detected early cannot show deep behavior). Train on sessions from the hardened and persistence configurations, or include the config as a feature and test transfer (EVAL 5.3).
- Candidate learners: logistic regression (baseline), gradient-boosted trees (LightGBM or equivalent), small GRU over the event sequence. Pick by validation PR-AUC; report all.
- Calibrate probabilities (temperature scaling or isotonic) on validation data; report calibration error.
- One model per stage, or one model with the stage as an input; decide by ablation.

### 7.2 Model A: LLM-agent detector (DEFERRED: side module, not part of the MVP)

- Binary primary task: LLM agent vs not-agent. Three-class (bot / human / agent) is secondary.
- **Shortcut risk.** Public agent logs come from a different harness and log format than Cowrie logs (DATA D2). A model trained to separate "public agent logs" from "Cowrie bot logs" can learn the log source rather than agent behavior. Therefore:
  1. Primary training positives are agent sessions **logged by our own Cowrie in the same format as negatives** (lab runs with ARACNE and PentestGPT using several open-weight models).
  2. The public dataset is used as an **external test set and for leave-one-model-out analysis**, using only features computable identically in both (command text, inter-command gaps defined consistently).
  3. Mandatory test: train on public data, test on our own; and train on ours, test on public. Report both.
- Negatives: replayed/real bot sessions, plus human volunteer sessions from our own Cowrie.
- Optional second signal: a passive canary text placed in our own honeypot's files, in the style of a prior LLM-agent honeypot that combined prompt injection and timing [S, CLAIMS P3]. Disclose it as optional and test it separately.

### 7.3 Features by stage (candidate list; computed identically offline and live)

| Stage | Available at | Features |
|---|---|---|
| S0 | TCP accept | visitor history: n_prev_sessions, highest_tier_served, last_value_label |
| S1 | after key exchange | client version string (normalized category), hassh (hashed category), counts of offered algorithms |
| S2 | after authentication | n_login_failed, time to first success, number of distinct usernames tried, success flag |
| S3 | session start | exec vs interactive, PTY present (terminal-size event), terminal width/height, count of forwarded env vars |
| S4 | first command | command length, token count, count of chaining operators, delay since login |
| S5 | first three commands | inter-command gaps (mean, min, std), distinct-command ratio, failed-command ratio |

Notes: A study of attacker clustering found HASSH too broad to correlate attacker IPs [S, CLAIMS P8], so do not assume it is a strong feature; measure it (SPIKES S5). Do not use raw credentials as features in the primary models (they enable shortcut learning on wordlists); an ablation may add hashed credentials.

## 8. Policy

Budgeted thresholding; thresholds tuned on validation data only.

```
def decide(visitor, stage, feats):
    p_v = model_v[stage](feats)
    p_a = model_a[stage](feats) if stage >= S3 else None
    if budget.exhausted():             return max(visitor.tier, T1)   # never downgrade
    if p_a is not None and p_a >= TAU_A[stage]:   target = T3
    elif p_v >= TAU_V3[stage]:                    target = T3
    elif p_v >= TAU_V2[stage]:                    target = T2
    else:                                          target = T1
    return max(visitor.tier, target)               # upward only
```

- `budget`: (a) maximum fraction of sessions escalated per day, (b) maximum concurrent T3 sessions (pool size). Both set before the live trial.
- Thresholds are chosen to meet an escalation budget on the validation set (for example the threshold at which 5%, 10% and 20% of sessions are escalated). Report results at several budgets, not one cherry-picked point.
- Policy `p1` is the rule above. A contextual bandit is a possible later variant and is **out of the minimum scope**.

## 9. Yield and cost definitions

### 9.1 Yield (session)

```
Y = w_cmd  * min(D, 20) / 20
  + w_file * 1[F >= 1]
  + w_pivot* 1[P >= 1]
  + w_ttp  * min(K, 8) / 8
D = number of distinct commands, F = file transfers, P = direct-tcpip requests,
K = number of distinct ATT&CK technique tags from the rule map (config/attack_map.yaml)
```
- Default weights are all 1 (pre-registered). Because weights are arbitrary, EVAL 6 requires a sensitivity analysis over random weights.
- Starter ATT&CK map (**IDs must be verified against attack.mitre.org before use [U]**): T1082 System Information Discovery (uname, /proc/cpuinfo), T1033 System Owner/User Discovery (id, whoami), T1057 Process Discovery (ps), T1083 File and Directory Discovery (ls, find), T1046 Network Service Discovery (netstat, ss), T1105 Ingress Tool Transfer (wget, curl, tftp), T1059.004 Unix Shell (chained shell invocation), T1053.003 Cron (crontab writes), T1098.004 SSH Authorized Keys (authorized_keys writes), T1070.004 File Deletion (rm of logs/artifacts), T1496 Resource Hijacking (miner indicators). Rules are simple, documented regexes; audit 100 sessions by hand to report rule precision.

### 9.2 Cost (session)

```
C = c_cpu * cpu_seconds + c_ram * gb_seconds + c_boot * vm_boots   (+ c_tok * tokens, LLM ablation only)
```
- Measure `cpu_seconds` and `gb_seconds` per tier from container/VM accounting during controlled load tests (SPIKES S2). Convert to rupees by allocating the VPS hourly price across measured resource shares. The allocation method and the price used are written into `results/cost_model.json`. Report both resource units and rupees.
- Idle cost (always-on T3 pool) is allocated across sessions served; state the method.

## 10. Configuration files

`config/identity.yaml`, `config/policy.yaml` (thresholds, budgets), `config/attack_map.yaml`, `config/arms.yaml` (arm definitions and assignment salt), `config/stages.yaml`. All versioned; every decision logs the version of each.

## 11. Milestones

| Phase | Deliverable | Exit criterion |
|---|---|---|
| 0 | **Gate 0:** spikes S1 and S3, Experiment 0 (S2, S4, S5 only if the gate passes) | `SPIKE_RESULTS.md` and `EXP0_RESULT.md` record the scope decision |
| 1 | Offline pipeline, labels, Model V, curves | EVAL H1 offline results reproducible by one command |
| 2 | T1/T2 sensor, gatekeeper, lab adversaries (Model A is DEFERRED, see section 0) | Lab runs logged; leave-one-model-out reported |
| 3 | T3 tier, public VPS, live trial, dashboard, human study | Trial finished at the pre-declared duration |
| 4 | Report and demo | All numbers regenerated from scripts |

Minimum viable cut (this is the project): Phase 0, Phase 1, T1/T2 persona comparison, cost model, dashboard of offline results. Phases 2 and 3 are gated by Gate 0 (section 0). T3, the live adaptive arm, Model A and the human study are future work unless the gates pass.

## 12. Risks

| ID | Risk | Mitigation |
|---|---|---|
| R1 | Per-session tier switching not feasible in Cowrie | Plan B (sticky routing), state the limitation |
| R2 | KVM unavailable on VPS, so T3 pool infeasible | Fallback ladder in 5.1; report as limitation |
| R3 | Too little live traffic for rare classes | Rare-class claims only from lab data; say so |
| R4 | Value label is not true intelligence value | Sensitivity analysis; manual audit of 100 sessions |
| R5 | Cowrie remains fingerprintable at the transport layer regardless of tier (HASSH server-side, banner) | Report residual detectability from the auditor; do not claim stealth |
| R6 | Overlap with published adaptive-honeypot work | Position per README 3; cite related work |
| R7 | Agent detector learns the harness/log source | Own-format positives, cross-source tests (7.2) |
| R8 | Identity mismatch across tiers | One identity profile; test with the auditor's OS-coherence checks |
| R9 | Dataset files are very large | Start with the 1.3 GB aggregation file; day subsets for event-level data |
| R10 | Cowrie security flaws | Pin a patched release; isolate; see SAFETY |

## 13. Open questions (must be answered by spikes or reading source)

1. Can Cowrie select persona per session in-process, and where? (S1)
2. Does the VPS expose KVM; what are boot time and per-session cost of T3? (S2)
3. What are the base rates of `value`, and which event fields exist in the real files? (S3)
4. Can Cowrie's server-side key-exchange algorithm list be changed to resemble OpenSSH, and does it matter to the auditor? (S4)
5. How informative is HASSH for value and agent prediction? (S5)
6. What is the license of the dataset authors' configuration repo? (S3)
