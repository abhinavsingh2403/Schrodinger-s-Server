# Schrödinger's Server

**A cost-aware adaptive SSH honeypot: spend expensive deception only where it pays.**

[![Pre-registration Tag: eval-v1](https://img.shields.io/badge/pre--registration-eval--v1-blue.svg)](https://github.com/abhinavsingh2403/Schrodinger-s-Server/tree/eval-v1)
[![Pre-registration Tag: exp0-v1](https://img.shields.io/badge/pre--registration-exp0--v1-blueviolet.svg)](https://github.com/abhinavsingh2403/Schrodinger-s-Server/tree/exp0-v1)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-green.svg)](LICENSE.rst)
[![Dataset: Zenodo 21260400](https://img.shields.io/badge/Dataset-Zenodo_21260400-orange.svg)](https://zenodo.org/records/21260400)
[![Cowrie: v3.1.6 Pinned](https://img.shields.io/badge/Cowrie-v3.1.6_pinned-brightgreen.svg)](https://github.com/cowrie/cowrie/tree/v3.1.6)

---

## 1. Project Overview & Core Thesis

In Internet-facing SSH honeypots, the overwhelming majority of sessions are one-shot automated scans and credential brute-force probes. A published LLM-honeypot deployment recorded **147,752 non-interactive sessions out of 148,850 total (99.26%)**, and only **150 interactive sessions (0.10%)** ([CLAIMS.md](CLAIMS.md) P2). This motivates the budgeted triage question (SPEC.md).

> Research question: can early session evidence guide escalation within a limited budget? Offline controls leave this question open.

---

## Project status

The native demo can switch an SSH session from T1 to T2 while preserving its connection. The three-day offline evaluation found **no validated ML gain**. At S4, the learned scorer, shuffled-label scorer and unweighted feature sum gave every test session the same selection probability across the three methods at the 10% budget. [Cutoff diagnosis](results/exp1/ROOT_CAUSE.md). S2 also failed its shuffle control, and S5 had too few held-out positives for a conclusion. [Demo runbook](docs/DEMO_RUNBOOK.md) · [Experiment 1 results](results/exp1/EXPERIMENT1_RESULT.md)

| Area | Completed and verified | Remaining work |
|---|---|---|
| Sensor and policy | Native Cowrie integration, same-session persona switching, durable session budgets and offline/live scoring parity. | Run the paired live-demo start/stop scripts end to end. Their recorded checks cover syntax and dry run. [Handoff](HANDOFF.md) |
| Dashboard and Docker | Decision-backed dashboard, masked identifiers and policy provenance. The Docker lab served SSH and dashboard traffic through loopback ports. | Verify distinct visitor identities through Docker ingress. Use native WSL for the returning-visitor demonstration today. [Handoff](HANDOFF.md) |
| Offline evaluation | Experiment 0 aggregate analysis and null-control diagnosis. Experiment 1 evaluated first auth, first command and third command with source-disjoint day splits. | Historical S1/S3 boundaries are unavailable. Any follow-up model comparison needs a fresh holdout. Boosting families await dependency approval. [Protocol](docs/EXPERIMENT1.md) |
| Resource measurements | Matched T1-final and T2-final workloads completed in one sensor process. | Isolated hardware or container costs by tier remain unmeasured. [Cost report](results/cost/COST_PER_TIER.md) |
| Studies and delivery | Participant protocol, masked export, working reports and demo runbook exist. | Run the human and persona-effect studies. H4 remains inconclusive. Held-out read-only trace replay completed in both Docker personas. [Replay results](results/replay/REPLAY_RESULT.md) · [Detector status](results/detector/DETECTOR_RESULT.md). Finish the reviewed report, slides and viva pack. T3 and public trials remain future work. [Study protocol](docs/STUDY_PROTOCOL.md) · [Checklist](docs/STATUS.md) |

The official weighted checklist records **52.5% (10.5/20)**. Experiment 1 is reported separately from the original Experiment 0 checklist. [Progress accounting](docs/STATUS.md)

### Known issues to fix or verify

| Issue | Observable effect | Next check |
|---|---|---|
| Docker edge hides the client address | Visitor memory merges distinct clients under one masked ID. | Verify that ingress preserves the source and that two loopback clients receive distinct masked IDs. [Handoff](HANDOFF.md) |
| S5 has different live and offline boundaries | Live dispatch starts on command two. Experiment 1 evaluates command three. | Agree on the intended live boundary and test dispatch on commands two and three before using the offline result for live decisions. [Protocol](docs/EXPERIMENT1.md) |
| Peak decision latency exceeds the sensor deadline | Threaded HTTP handling improved the measured workload, but some round trips still exceeded 200 ms. | Measure sensor fallback events alongside round-trip latency under concurrent load. [Concurrency probe](results/cost/concurrency_probe.json) |
| IPv4 audit remains open | The audit reports FAIL with findings listed by file and line. | Reconcile the findings with the audit rules and retain visibility of unexpected addresses. [Safety audit](results/safety_check.json) |
| Experiment 1 fixture tests require an explicit command | Default pytest discovery skips their filenames. | Run the command below until discovery includes both fixtures. [Test configuration](pytest.ini) |

Experiment 1 found no validated ML gain on the audited days. S2 and S4 failed the shuffle control, and S5 was underpowered. [Experiment 1 results](results/exp1/EXPERIMENT1_RESULT.md).

Weighted checklist completion: **52.5%** (10.5/20) (see `docs/STATUS.md`). The [handoff](HANDOFF.md) records verification scope. `LAB_DEMO_NOT_ML` demonstrates policy mechanisms only.

---

## 2. Verified Evidence Summary

- **Early ML Evaluation (Exploratory — No Confirmed ML Claim)**: Post-hoc exploratory S3 evaluation on frozen splits (`50000` train, `100793` reached test, `8619` positives) shows label-free negative activity on retained columns achieves recall `0.648992` (PR-AUC `0.398257`), whereas the converged trained scorer (`All`, step `5532`) achieves recall `0.306654` (PR-AUC `0.352775`) and its shuffled-label control (`Shuffle`, step `1000`) achieves recall `0.305613` (`INCONCLUSIVE (INVALID shuffle)`) (see `results/exp0/POSTHOC_ML_EVAL.md`). Removing volume features (`Volume removed`, step `5529`) yields recall `0.111804` (`REJECTED`, equal to its shuffled control `0.111804`) (see `results/exp0/POSTHOC_ML_EVAL.md`). Constant-target fallback analysis confirms `session.params` dominates the null cutoff (`0.649042` vs archived real `0.291966`) (see `results/exp0/NULL_ROOT_CAUSE.md`). Pre-command validity is not certifiable on the audited archive (`0` verified historical S3 decision boundaries across `12380945` events and `184383` complete command sessions over `3` sampled days) (see `results/exp0/PRECOMMAND_NOT_VERIFIABLE.md`).
- **Event-Level Prefix Logging**: Opt-in (`SENSOR_PREFIX_LOG`, off by default) per-process JSONL logging on the native launcher records masked `session`, `event`, `event_time`, `observed_at`, and `seq` (without commands, credentials, or addresses), plus decision-boundary markers with `last_seq` and numeric `features` (see `docs/EVENT_LOG.md`). Consistency checks on lab-generated data only (`scope: LAB`) succeeded across `run_bot_like` (5 sessions, 3 S3 markers, 2 early closes), `run_interactive` (6 sessions, 6 S3 markers), `run_slow_recon` (1 session, 1 S3 marker), and `run_transfer_like` (3 sessions, 3 S3 markers), with `0` `reached_without_marker` and `0` `errors` (see `results/study/marker_consistency.json`).
- **Cost measurement.** In matched LAB_DEMO hostname sessions, repeat-index differences (T2-final minus T1-final) ranged from -0.25 to +0.66 percentage points for mean CPU and +0.48 to +1.14 MB for mean memory. The workloads share one sensor process and differ in PTY allocation. Sampling includes pauses and early T1 time. The DEFAULT authentication trigger and historical mixed runs are recorded in [the cost report](results/cost/COST_PER_TIER.md).
- **Human Study Kit**: The lab participant protocol (`docs/STUDY_PROTOCOL.md`) and export/evaluation commands (`docs/EVENT_LOG.md`) exist, but the human study is `NOT RUN` (see `docs/EVENT_LOG.md`, `HANDOFF.md`).
- **Docker Lab Topology**: `infra/docker-compose.yml` defines four services (`edge`, `sensor`, `gatekeeper`, `dashboard`), with only `edge` publishing ports on loopback (`127.0.0.1:2222` and `127.0.0.1:8080`) and the remaining services isolated on `internal_honeypot_net` (`internal: true`); direct-IP and named sensor egress failed in the observed check (see `HANDOFF.md`, `infra/docker-compose.yml`). Because `edge` merges client source addresses, Docker serves as an isolation demonstration only; multi-visitor and returning-visitor scenes are native-WSL only (see `HANDOFF.md`).
- **Native Demo Runbook**: `docs/DEMO_RUNBOOK.md` and `harness/demo/` (`start_live_demo.sh`, `stop_live_demo.sh`, `run_showcase.sh`, `run_lab_demo.sh`) provide scripted lab demonstrations (`LAB_DEMO_NOT_ML`). The live launcher scripts (`start_live_demo.sh` / `stop_live_demo.sh`) are syntax-checked and dry-run checked, and are not yet run live on real services (see `HANDOFF.md`).
- **Future Work**: Deferred items from `SPEC.md` and `EVAL.md` are: T3 sandboxed guest (`SPEC.md`), public randomized live trial (`EVAL.md` 5.6), human blind study (`EVAL.md` 5.5), persona-effect natural experiment (`EVAL.md` 5.3), third-party detector evaluation (`EVAL.md` 5.5 / H4), and broader replay beyond the read-only subset ([measured subset](results/replay/REPLAY_RESULT.md)).

## 3. Data Provenance & Ground Truth

All empirical analysis is performed on open-access, peer-reviewed research data.

### Primary Dataset: D1 (Zenodo Record 21260400)
- **Title**: Large-Scale Empirical Dataset of 38 Million SSH Honeypot Sessions
- **Source URL**: `https://zenodo.org/records/21260400`
- **License**: Creative Commons Attribution 4.0 International (CC-BY 4.0)
- **Direct Download URL**: `https://zenodo.org/api/records/21260400/files/session_aggregation.jsonl.gz/content`
- **File Name**: `data/session_aggregation.jsonl.gz` (Gitignored per security rules)
- **File Size**: `1,328,104,319 bytes` (~1.33 GB compressed)
- **Expected MD5**: `1f3897650fb420c97c14ff452398c3f8`
- **Computed MD5**: `1f3897650fb420c97c14ff452398c3f8` (**MATCH**, verified via `analysis/verify_download.py`)

### Dataset Ground Truth Findings ([results/base_rates.json](results/base_rates.json))
Computed over the complete dataset using DuckDB with zero dropped sessions:
- **Total Sessions Analyzed**: `38,126,048`
- **Temporal Span**: `52 continuous calendar days` (2025-06-27 to 2025-08-17 UTC)
- **Schema Conformity**: Exact match on all **25 schema fields** listed in `DATA.md`
- **Login Success Count**: `4,374,446` (11.47% authentication success rate)
- **Command Input Sessions**: `3,335,870` (8.75%)
  - Zero commands (pure probe): `34,790,178` (91.25%)
  - 1–4 commands: `2,185,616` (5.73%)
  - 5–9 commands: `992,305` (2.60%)
  - 10+ commands: `157,949` (0.41%)
  - Command Quantiles: **p50 = 0, p90 = 0, p99 = 2**
- **File Transfers**: `755,225` sessions (1.98%)
- **Direct-TCPIP Requests (Pivoting)**: `467,551` sessions (1.23%)
- **Aggregate Value=1 Base Rate (`N_CMD >= 5 OR file transfer OR pivot`)**: **3.23% (1,232,570 sessions)**
  - Confirms a realistic, non-degenerate class imbalance well-suited for early stage triage and PR-AUC evaluation.

---

## 4. Key Engineering Milestones Completed

### 1. Pinned Cowrie Upstream Audit (Tag `v3.1.6`)
- Pinned commit hash: `ea9513eda9ea0dac05f6ace7db84ca95e0571501`
- Read-only audit copy stored in `sensor/cowrie-src/`
- Full code path traceability verified with line-number citations across:
  - SSH Transport & Banner: `src/cowrie/ssh/transport.py:72`, `src/cowrie/ssh/factory.py:107`
  - Key Exchange & HASSH: `src/cowrie/ssh/transport.py:258-281`
  - User Authentication: `src/cowrie/ssh/userauth.py:134`, `src/cowrie/shell/realm.py:22`
  - Shell & Fake Filesystem: `src/cowrie/shell/session.py:48`, `src/cowrie/shell/fs.py:126`, `src/cowrie/core/honeyfs.py:65`
  - Command Dispatch: `src/cowrie/shell/honeypot.py:932`, `src/cowrie/shell/protocol.py:246`
  - Proxy/Pool Backend Selection: `src/twisted/plugins/cowrie_plugin.py:162`

### 2. Spike S1 Outcome: Plan A (In-Process Hook) Verified
- **Question**: Can Cowrie choose the persona per session after login without a deep fork?
- **Finding**: **YES.** Subclassing Twisted Conch's session adapter (`cowrie.shell.session.SSHSessionForCowrieUser`) allows dynamic persona assignment (hostname, custom filesystem overlay) with **0 lines changed in Cowrie core**. Merge-pain risk on upstream updates is near zero.
- **Proof-of-Concept**: [`sensor/spike_s1_poc.py`](sensor/spike_s1_poc.py) verified:
  - Session A (odd client port) assigned Persona 1 (`web-srv-01`, Ubuntu 22.04 T2 persona).
  - Session B (even client port) assigned Persona 2 (`generic-srv-02`, Debian 12 T1 persona).
  - Automated test suite: [`sensor/test_spike_s1_poc.py`](sensor/test_spike_s1_poc.py) passing (`2 passed`).

### 3. Pre-Registration Enforced
- Git tags applied to lock experimental hypotheses prior to model training:
  - `eval-v1`: Locks evaluation metrics, success criteria, and label definitions.
  - `exp0-v1`: Locks Experiment 0 protocol per `EXPERIMENT0.md`.

---

## 6. Proposed architecture (T3 is future work)

```
                         Internet (attackers, scanners, bots)
                                      |
                              [ VPS Firewall ]
                                      |
                     +----------------+-----------------+
                     |     Twisted Conch Router         |   Plan A: In-process hook
                     | (AdaptiveSSHSession Adapter)     |   (Verified in Spike S1)
                     +--------+---------------+---------+
                              |               |
                      +-------+--+     +------+-----+      +-----------------+
                      | T1 Lite  |     | T2 Hardened|      | T3 Real VM      |
                      | Cowrie   |     | Cowrie     |      | Cowrie proxy -> |
                      | shell    |     | shell+fs   |      | sandboxed guest |
                      +-------+--+     +------+-----+      +--------+--------+
                              \               |                     /
                               +---- Cowrie JSON Event Logs -------+
                                              |
                                   +----------v----------+
                                   |     Gatekeeper      |
                                   | stage features,     |
                                   | Model V, policy,    |
                                   | visitor memory      |
                                   +----------+----------+
                                              |
                           +------------------+-------------------+
                           |                                      |
                   Decision Log (SQLite)                 Dashboard (read-only)
```

---

## 7. Repository Layout

```
Schrodinger-s-Server/
├── README.md               # Project overview, status, data provenance, roadmap
├── SPEC.md                 # System specification: architecture, components, models
├── EVAL.md                 # Pre-registered evaluation plan (Tag: eval-v1)
├── DATA.md                 # Dataset specifications, schema definitions, hashes
├── SPIKES.md               # Go/no-go technical spike specifications
├── SPIKE_RESULTS.md        # Recorded outcomes of completed spikes (S1, S3)
├── EXPERIMENT0.md          # Gate 0 Experiment specification (Tag: exp0-v1)
├── WEEK1.md                # Day-by-day execution plan and gating criteria
├── SAFETY.md               # Legal, ethical, and operational safety rules
├── AGENTS.md               # System and agent coding standards
├── CLAIMS.md               # Ledger of verified external claims ([V]/[S]/[U])
├── DECISIONS.md            # Architecture Decision Records (ADRs)
├── HANDOFF.md              # Cross-agent state and progress ledger
├── requirements.txt        # Pinned dependencies (duckdb==2.0.0, pytest==9.2.0)
├── analysis/               # Offline data pipelines and verification scripts
│   ├── s3_base_rates.py    # 38M session DuckDB base rate pipeline
│   ├── test_s3_base_rates.py # Unit tests for base rate logic and schema checks
│   ├── verify_download.py  # Streaming chunked MD5 file verification tool
│   └── test_verify_download.py # Pytest test suite for verifier
├── sensor/                 # Honeypot sensor components and study copy
│   ├── cowrie-src/         # Pinned Cowrie v3.1.6 source tree (gitignored)
│   ├── spike_s1_poc.py     # Spike S1 in-process persona switching proof-of-concept
│   └── test_spike_s1_poc.py # Unit test suite for S1 PoC
├── data/                   # Dataset store (gitignored)
│   └── README.md           # Download ledger with verified checksums
├── results/                # Script-generated outputs (never hand-edited)
│   ├── base_rates.json     # Empirical base rates from 38,126,048 sessions
│   └── MANIFEST.json       # Run manifest: hashes, versions, commit IDs, timestamps
├── infra/                  # Infrastructure scripts and firewall definitions
├── gatekeeper/             # Feature extractor, Model V, and visitor memory
├── router/                 # In-process escalation hooks
├── harness/                # Lab test harness and adversary runners
└── dashboard/              # Read-only offline visualization dashboard
```

---

## 8. Reproducibility & Running Tests

### Environment Setup
Python 3.12+ with virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### Run Unit Tests
```powershell
.\.venv\Scripts\python -m pytest -q
```
Recorded Windows suite result: **267 passed, 3 skipped**. Run the two Experiment 1 fixtures explicitly:

```powershell
python -m pytest -q analysis/experiment1_dataset_test.py analysis/experiment1_eval_test.py
```

Experiment 1 parquet tables are generated locally and ignored by Git. The protocol and cohort results are tracked. [Reproduction commands](HANDOFF.md) · [Cohort counts](results/exp1/cohorts.json)

### Live Honeypot Demonstration (Native WSL — Path A)
Follow the [native demo runbook](docs/DEMO_RUNBOOK.md).

### Reproduce Spike S1 Persona Switching PoC
```bash
python sensor/spike_s1_poc.py
python -m pytest sensor/test_spike_s1_poc.py
```

### Run Base Rates on 38 Million Sessions
```powershell
.\.venv\Scripts\python analysis/s3_base_rates.py --file data/session_aggregation.jsonl.gz --n-cmd 5
```

---

## 9. Non-Negotiable Safety & Ethics Rules
Per [`SAFETY.md`](SAFETY.md):
1. **Offline Phase 0**: All early work uses public datasets and lab mock loops. No network-facing exposure.
2. **Zero Fabrication**: Every reported metric and table value originates from a script. Never typed by hand.
3. **No Attacks**: No scanning, probing, or counter-exploitation of third-party systems.
4. **Data Protection**: Raw attacker IPs are never committed. Analysis uses salted HMAC IDs.
5. **Malware Safety**: Captured files are never executed. `transferred_files.zip` is strictly banned from download.

---

## 10. References & Literature Cited

All external datasets, academic papers, and security frameworks are tracked with their verification statuses in [`CLAIMS.md`](CLAIMS.md).

### Datasets & Data Descriptors
- **[D1] Large-Scale Empirical Dataset of 38 Million SSH Honeypot Sessions** (2025/2026). Zenodo Record 21260400. DOI: [`10.5281/zenodo.21260400`](https://zenodo.org/records/21260400). Licensed under CC BY 4.0.
  - Data Descriptor in press: *Nature Scientific Data* (2026), DOI: [`10.1038/s41597-026-08668-0`](https://doi.org/10.1038/s41597-026-08668-0).
- **[D2] Honey for the Agent Dataset** (2026). Multi-environment LLM attacker traces on five SSH targets. Zenodo Record 20818246. DOI: [`10.5281/zenodo.20818246`](https://zenodo.org/records/20818246). Licensed under CC BY 4.0.
- **[D3] Beyond Bots Dataset** (2026). Empirical SSH probe traces with heuristic indicators. Zenodo Record 19610238. DOI: [`10.5281/zenodo.19610238`](https://zenodo.org/records/19610238).

### Academic Papers & Preprints
- **[P1] Explainability-Driven Adaptive Deception Control System on Cowrie** (2026). Proposes random-forest behavioral profiling with epsilon-greedy Q-learning strategy selection. *Scientific Reports* (Nature Portfolio). DOI: [`10.1038/s41598-026-64427-6`](https://www.nature.com/articles/s41598-026-64427-6).
- **[P2] Multi-Agent LLM SSH Honeypot Deployment** (2026). Empirical measurement of 148,850 honeypot sessions showing a 99.26% non-interactive automation rate. arXiv:2606.27990. [`https://arxiv.org/abs/2606.27990`](https://arxiv.org/abs/2606.27990).
- **[P3] Palisade: LLM Agent Honeypot with Prompt-Injection and Timing Analysis** (2024). Active and passive behavioral fingerprinting of autonomous agents over 8M attempts. arXiv:2410.13919. [`https://arxiv.org/abs/2410.13919`](https://arxiv.org/abs/2410.13919).
- **[P4] Honey for the Agent: Behavioral Differences Across Environments & Early Attacker Fingerprinting** (Sept 2026). Evaluates cross-environment model identification and early session fingerprinting. *ResearchGate Publication*.
- **[P5] Rouxii: AI Pentesters That Detect and Exploit Honeypots** (2026). Analysis of honeypot fingerprinting surfaces, single-packet identification across 7,605 instances, and Cowrie attack surface auditing. arXiv:2609.26555. [`https://arxiv.org/abs/2609.26555`](https://arxiv.org/abs/2609.26555).
- **[P6] LLM-Based Penetration Testing in the Presence of Honeypots** (2026). Budget-aware ranking, pre-connect screening, and stopping rules for autonomous attack agents. arXiv:2609.08093. [`https://arxiv.org/abs/2609.08093`](https://arxiv.org/abs/2609.08093).
- **[P7] Local-LLM SSH Honeypots and Automated Evaluation Benchmarking** (2026). Architectural survey of local LLM honeypot backends and proxy emulation. arXiv:2608.18686. [`https://arxiv.org/abs/2608.18686`](https://arxiv.org/abs/2608.18686).
- **[P8] A Measurement Study of Attackers on Medium-Interaction Honeypots and HASSH Limitations** (2022). Evaluation of 2.6M successful logins demonstrating that HASSH fingerprints are too broad for granular attacker correlation. arXiv:2206.13614. [`https://arxiv.org/abs/2206.13614`](https://arxiv.org/abs/2206.13614).
- **[P9] Classification of Human, Automated, and AI-Assisted SSH Attackers from Session Features** (2024). Session feature engineering and classification under severe class imbalance (6,231:1). Rochester Institute of Technology (RIT) Master's Thesis. [`https://repository.rit.edu/theses/12605/`](https://repository.rit.edu/theses/12605/).
- **[P10] Improvement of Cowrie Honeypot Interaction and Deception Capabilities** (2025). Survey on honeypot fingerprinting mitigation, filesystem persistence, and interaction depth. *ResearchGate Survey*.
- **[P11] Inter-Command Gap Analysis in SSH Honeypot Bot Detection** (2024). Heuristic scoring of human vs bot interaction using command arrival intervals. [`https://github.com/Mukundmishra13/ssh-honeypot`](https://github.com/Mukundmishra13/ssh-honeypot).

### Security Tools, Frameworks & Standards
- **[T1–T4] Cowrie SSH/Telnet Honeypot** (Michel Oosterhof, Upi Tamminen). Medium-to-high interaction honeypot engine. Pinned at release `v3.1.6` (`ea9513eda9ea0dac05f6ace7db84ca95e0571501`). Licensed under BSD-3-Clause. [`https://github.com/cowrie/cowrie`](https://github.com/cowrie/cowrie) / [`https://docs.cowrie.org`](https://docs.cowrie.org).
- **[T5] honeypot-auditor**: Automated honeypot detection tool evaluating shell semantics, OS coherence, HASSH, and TCP latency. Licensed under MIT. [`https://pypi.org/project/honeypot-auditor/`](https://pypi.org/project/honeypot-auditor/).
- **[T6] ARACNE**: Autonomous LLM-driven SSH penetration testing agent supporting local Ollama models. Stratosphere Laboratory (GPL-2.0). [`https://github.com/stratosphereips/aracne`](https://github.com/stratosphereips/aracne).
- **[T7] PentestGPT**: LLM-empowered penetration testing framework for automated security assessment. Licensed under MIT. [`https://github.com/GreyDGL/PentestGPT`](https://github.com/GreyDGL/PentestGPT).
- **[T8] HASSH**: Cryptographic SSH client and server fingerprinting standard based on key exchange algorithm negotiation. Salesforce / Corelight. [`https://github.com/salesforce/hassh`](https://github.com/salesforce/hassh).
- **[T9] Fake Honeypots: Deception Through Apparent Vulnerability** (Rowe et al.). Naval Postgraduate School. [`https://faculty.nps.edu/ncrowe/fakehoney.htm`](https://faculty.nps.edu/ncrowe/fakehoney.htm).
