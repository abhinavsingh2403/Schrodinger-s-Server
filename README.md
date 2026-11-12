# Schrödinger's Server

**A cost-aware adaptive SSH honeypot: spend expensive deception only where it pays.**

[![Pre-registration Tag: eval-v1](https://img.shields.io/badge/pre--registration-eval--v1-blue.svg)](https://github.com/abhinavsingh2403/Schrodinger-s-Server/tree/eval-v1)
[![Pre-registration Tag: exp0-v1](https://img.shields.io/badge/pre--registration-exp0--v1-blueviolet.svg)](https://github.com/abhinavsingh2403/Schrodinger-s-Server/tree/exp0-v1)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-green.svg)](LICENSE.rst)
[![Dataset: Zenodo 21260400](https://img.shields.io/badge/Dataset-Zenodo_21260400-orange.svg)](https://zenodo.org/records/21260400)
[![Cowrie: v3.1.6 Pinned](https://img.shields.io/badge/Cowrie-v3.1.6_pinned-brightgreen.svg)](https://github.com/cowrie/cowrie/tree/v3.1.6)

---

## 1. Project Overview & Core Thesis

In Internet-facing SSH honeypots, the overwhelming majority of sessions are one-shot automated scans and credential brute-force probes. A published LLM-honeypot deployment recorded **147,752 non-interactive sessions out of 148,850 total (99.26%)**, and only **150 interactive sessions (0.10%)** ([CLAIMS.md](CLAIMS.md) P2). Serving high-interaction deception (rich emulated environments, real sandboxed VMs, or LLM-driven backends) indiscriminately wastes significant compute and financial budget on shallow noise.

> **Central Thesis:** A lightweight, cost-aware **gatekeeper** can infer early in an SSH session (handshake, authentication, or first command) whether the attacker is likely to yield interactive intelligence, escalating high-value visitors to higher-fidelity deception personas while serving cheap default emulation to automated noise—maximizing **intelligence yield per rupee**.

---

## 2. Project Completion Status & Progress Accounting

> **Branch Notice:** Active engineering code, empirical pipelines, and test suites live on branch **[`trainmodel`](https://github.com/abhinavsingh2403/Schrodinger-s-Server/tree/trainmodel)**.

### Realistic Maturity Assessment (No Overexaggeration)
Following rigorous external peer audit, completion metrics are recalibrated to distinguish isolated unit-tested components from a live, operating end-to-end deployment:

| Dimension | Progress | Assessment Rationale |
|---|:---:|---|
| **Standalone Subsystems (Code & Mock Tests)** | **~70%** | 93 passing unit tests across gatekeeper, sensor, router, harness, infra, analysis, and dashboard. Individual components function in unit tests, but are not yet fully wired to live Cowrie hooks. |
| **Offline Data & Science** | **~65%** | Base rates S3 Part 1 verified (38.1M sessions); event schema verified; Gate 0 evaluated on 598k test sessions as an aggregate-data proxy ($N_{\text{cmd}} \ge 5$); cluster bootstrap needs dynamic threshold recalculation. |
| **Live Integration & End-to-End Deployment** | **~35%** | Docker volumes mount custom sensor; feature keys reconciled; session recording hooked; pending live Cowrie in-process event hook registration and Kali Linux validation. |
| **True Overall Project Completion** | **~55–60%** | Strong, original research prototype (rated ~7.2/10). Solid scientific grounding, but bridge between mock unit tests and live operational defense remains to be crossed. |

```
[████████████████████████████░░░░░░░░░░░░░░░░░░░░░░] ~55–60% True Overall Maturity
[███████████████████████████████████░░░░░░░░░░░░░░░] ~70% Standalone Subsystems
[████████████████████████████████░░░░░░░░░░░░░░░░░░] ~65% Offline Science
[█████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] ~35% Live Integration
```

| Phase / Component | Scope | Status | Honest Details / Audit Reality |
|---|---|---|---|
| **G1: Repo Skeleton & Pinning** | Core | **DONE** | Python 3.12, DuckDB 2.0.0, Pytest 9.2.0 pinned |
| **G2: Streaming Verifier Tooling** | Core | **DONE** | Chunked MD5 streaming verifier (`verify_download.py`) |
| **S3 Part 1: Aggregate Base Rates** | Core | **DONE** | 38.1M sessions analyzed; value=1 base rate = 3.23% (`results/base_rates.json`) |
| **S3 Part 2: Event Archive Verification** | Core | **DONE** | Range request inspection of 19.4GB `data_all.zip`; confirmed 52 days and `group \in {1, 2, 3, 4}` |
| **S1: Cowrie Persona Switching PoC** | Core | **DONE** | Plan A in-process Conch adapter subclass verified in mock loop (`sensor/spike_s1_poc.py`) |
| **O3: Experiment 0 (`EXPERIMENT0.md`)** | Core (Gate 0) | **DONE (Outcome: FAIL)** | Evaluated on 598,647 test sessions without feature leakage. Evaluates aggregate proxy ($N_{\text{cmd}} \ge 5$); cluster bootstrap needs dynamic threshold recalculation across resamples. |
| **Phase 1: Gatekeeper Engine & Memory** | MVP | **BUILT (Code/Tests)** | SQLite WAL visitor memory, upward-only policy with budget ceiling, parity extractor, decision API; feature keys reconciled with sensor. |
| **Phase 1: Sensor & Router Subsystems** | MVP | **BUILT (Mock-Tested)** | Adaptive Conch session server (`sensor/`), Plan B sticky asyncio router (`router/`); pending live Cowrie event hook registration. |
| **Phase 2: Adversary Harness & Infra** | MVP | **BUILT (Code/Tests)** | Detector runner with safety allowlist, synthetic replay engine, isolated docker compose with custom sensor volume mount. |
| **Phase 2: Cost & Arm Simulation** | MVP | **ORACLE BOUND** | Nominal cost model; Arm D labeled as retrospective hindsight upper bound (`results/arm_simulation.json`). |
| **EVAL 5.3: Persona Natural Experiment** | MVP | **PENDING DATA** | Blocked on event-level `group` ingestion from `data_all.zip` (field absent in `session_aggregation`). |
| **Phase 2: Results Dashboard** | MVP | **BUILT (Code/Tests)** | Cyber Protocol theme, privacy masking (`vis_xxxx`), zero npm dependencies, `/api/exp0` endpoint added. |
| **Phase 3: Live VPS Trial / T3 VM Pool** | Post-MVP | **DEFERRED** | Dependent on Linux testbed with Twisted Conch runtime and live honeypot exposure. |

---

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
- **Login Success Count**: `4,374,446` (11.47% authentication pass rate)
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

## 5. Prioritized Engineering & Scientific Action Plan

```mermaid
flowchart TD
    subgraph Done["Current State: Research Prototype (~55-60%)"]
        S1["S1: Cowrie Persona Mock PoC"]
        S3["S3: 38M Base Rates & Range Checks"]
        EXP0["Exp 0 Gate 0: Evaluated on 598k Sessions (FAIL)"]
        GK["Gatekeeper Engine + SQLite Memory + Budget Ceiling"]
        DASH["Dashboard Server & Telemetry API"]
    end

    subgraph Priorities["6-Step Prioritized Action Plan to Reach 100%"]
        P1["1. Correct Cluster Bootstrap & Recalculate S3 CI"]
        P2["2. Solidify Live Rule Gatekeeper & Wire Visitor Memory"]
        P3["3. Wire Cowrie Event Hooks & Mount Custom Plugin"]
        P4["4. Live Kali Linux vs Ubuntu Practical Lab Test"]
        P5["5. Independent Security Audit (honeypot-auditor)"]
        P6["6. Lock Git Release Tags (exp0-v3 / eval-v3)"]
    end

    EXP0 --> P1
    GK --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> P6

    style Done fill:#0f172a,stroke:#38bdf8,stroke-width:1px,color:#fff
    style Priorities fill:#1e1b4b,stroke:#a855f7,stroke-width:1px,color:#fff
```

### Technical Audit Findings & Remediation Roadmap

Based on rigorous peer audit, the following 5 technical items must be addressed before presenting Schrödinger's Server as an operational deployment:

1. **Bootstrap Procedure Correction (Priority 1)**:
   * *Audit Finding*: The current `paired_cluster_bootstrap_delta()` in `analysis/exp0_train.py` computes the top 10% threshold globally on the initial test set and resamples only positive-containing IP clusters across 1,000 resamples.
   * *Action*: Resample all clusters with replacement, dynamically recalculate the top 10% selection threshold inside each bootstrap draw, and scale to the pre-registered 10,000 resamples to produce mathematically rigorous confidence intervals.
   * *Status on S3*: At Stage S3, the point improvement is promising ($\Delta_3 = +17.68$ pp), but the wide CI ($[-0.24, +60.52]$ pp) indicates high statistical uncertainty rather than rule superiority. The correct conclusion is that superiority is *not statistically established*.

2. **Finish the Live Rule-Based Gatekeeper (Priority 2)**:
   * *Audit Finding*: Sensor feature keys (`login_success`, `n_login_failed`) were mismatched with gatekeeper fallback keys (`s2_has_success`, `s2_failed_logins`), and visitor memory lacked an automated session termination hook.
   * *Action Completed*: Feature key reconciliation is now integrated in `gatekeeper/decision_api.py`, and `record_session()` is wired to `AdaptiveSessionAdapter.on_session_closed()` to persist visitor tier history upon session completion.

3. **Connect Cowrie In-Process Event Hooks (Priority 3)**:
   * *Audit Finding*: Docker Compose ran vanilla `cowrie/cowrie:v3.1.6` without mounting custom sensor adapters.
   * *Action*: Volume mount `../sensor` into `/cowrie/cowrie-git/src/cowrie/custom_sensor` and wire Conch's `SSHService.ssh_CHANNEL_OPEN` to dynamically assign and switch filesystem overlays based on Gatekeeper decisions.

4. **Live Linux Practical Testbed (Priority 4)**:
   * *Audit Finding*: Unit tests pass in isolated mock loops, but end-to-end operation against real attacker tools has not been executed on live Linux/Kali environments.
   * *Action*: Deploy honeypot on an Ubuntu lab host, execute automated scans and brute-force attacks from Kali Linux (Nmap, Hydra, SSH), and verify in real time that sessions are dynamically routed and logged in the dashboard.

5. **Independent Security Audit (Priority 5 - EVAL H4)**:
   * *Audit Finding*: In-repo detector runner tests check internal heuristics rather than independent third-party scanning.
   * *Action*: Run `kaniini/honeypot-auditor` against the running honeypot container from an isolated network to verify zero Cowrie giveaways and strict OS coherence.

6. **Documentation & Release Synchronization (Priority 6)**:
   * Apply official git tags (`exp0-v3`, `eval-v3`) to seal the leak-free baseline code and results. Maintain complete transparency in reports and viva presentations.

---

## 6. Architecture

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
.\.venv\Scripts\python -m pytest analysis/
```

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
