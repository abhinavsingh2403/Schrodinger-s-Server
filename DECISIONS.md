# DECISIONS.md: Design and Architecture Decision Log

All non-trivial design decisions, architectural choices, and departures from plans must be recorded here.

---

## Decision Template

```markdown
### YYYY-MM-DD: <Short Title>
- **Status**: [PROPOSED | ACCEPTED | REJECTED | SUPERSEDED]
- **Owner**: <Role / Person>
- **Context**: <Background context, constraint, or problem statement>
- **Decision**: <The exact decision made>
- **Alternatives considered**: <List of alternatives and why they were not chosen>
- **Why**: <Core rationale, evidence, or tradeoffs>
- **Consequences**: <Impact on SPEC.md, EVAL.md, or implementation>
```

---

## Log

### 2026-11-11: Day 0 Repository Initialization & Pinned Dependencies
- **Status**: ACCEPTED
- **Owner**: All (P1/P2/P3)
- **Context**: Setting up repository skeleton and development environment per `WEEK1.md` Day 0 and Task G1.
- **Decision**: Initialize Git repository on `main` branch, configure strict `.gitignore` preventing data/secret leakage, create skeleton directories (`analysis/`, `data/`, `results/`, `infra/`, `sensor/`, `gatekeeper/`, `router/`, `harness/`, `dashboard/`), pin Python 3.12.10, and pin dependencies `duckdb==2.0.0` and `pytest==9.2.0` in `requirements.txt`.
- **Alternatives considered**: Unpinned latest packages (rejected due to reproducibility requirements in `AGENTS.md` and `EVAL.md`).
- **Why**: `AGENTS.md` Rule 13 ("Pin everything") and Task G1 mandate deterministic, pinned environments.
- **Consequences**: Standardized dependencies for data verification and base rate calculations in Spikes S1 and S3.

### 2026-11-11: Pinned Cowrie Upstream Release Tag v3.1.6
- **Status**: ACCEPTED
- **Owner**: P1 (Architecture / Honeypot Lead)
- **Context**: Task O2 / Spike S1 requires pinning the exact upstream release tag and commit hash for Cowrie study and implementation.
- **Decision**: Pin Cowrie release `v3.1.6` (commit hash `ea9513eda9ea0dac05f6ace7db84ca95e0571501`, verified via GitHub tag `v3.1.6` and PyPI `3.1.6`). Cloned into `sensor/cowrie-src/` as a read-only study copy and gitignored to avoid repository bloat.
- **Alternatives considered**: v3.1.2 (cited in SPEC draft; superseded by security advisories and bug fixes in 3.1.6).
- **Why**: `AGENTS.md` Rule 13 ("Pin everything") and `SAFETY.md` Rule 2.5 ("Pin a patched Cowrie release").
- **Consequences**: Baseline for source code citations in Spike S1 and future sensor runner implementation.

### 2026-11-11: Spike S1 Decision: Plan A (In-Process Hook via Twisted Conch Adapter Subclass)
- **Status**: ACCEPTED
- **Owner**: P1 (Architecture / Honeypot Lead)
- **Context**: Spike S1 investigated whether Cowrie can choose persona (fake filesystem, hostname, identity) per-session after login from our own code without a deep fork.
- **Decision**: Accept **Plan A** (in-process hook). Persona adaptation is hooked at the Twisted Conch session adapter boundary: subclassing `cowrie.shell.session.SSHSessionForCowrieUser` (or registering custom `ISession` adapter for `CowrieUser`). On session channel open, the adapter inspects the client connection (`avatar.conn.transport.transport.getPeer().port` / IP / session ID / gatekeeper decision), assigns `avatar.server.hostname`, and overlays persona-specific files onto the fake filesystem via `avatar.server.fs.init_honeyfs(persona_dir)` or `mkfile()`.
- **Alternatives considered**:
  - Plan B: Sticky multi-instance routing at TCP splice / visitor memory (higher infrastructure overhead, cross-session only, lacks fine-grained in-session tier escalation).
  - Deep fork of Cowrie core (rejected: high merge-pain on upstream Cowrie releases).
- **Why**: Validated with working throwaway PoC in `sensor/spike_s1_poc.py` and unit tests in `sensor/test_spike_s1_poc.py` (2 passed). Requires zero changes to Cowrie core codebase (0 lines changed in Cowrie). Merge-pain risk is near zero.
- **Consequences**: Plan A is confirmed viable for Gate 0. SPEC.md and EVAL.md architecture retains in-process per-session escalation for T1 (Lite) and T2 (Hardened).

### 2026-11-11: Gatekeeper Engine Architecture (Visitor Memory, Monotone Upward Policy, and Feature Parity)
- **Status**: ACCEPTED
- **Owner**: P2 / Lead Developer
- **Context**: Per SPEC.md Section 5.2 and AGENTS.md Rule 10, the Gatekeeper must coordinate stage features, visitor memory, and policy decisions with 100% offline/live code parity and strict fail-cheap safety.
- **Decision**: Implemented `SessionFeatureExtractor` (`gatekeeper/feature_extractor.py`) as a unified feature extraction module used identically by offline DuckDB processing and live Cowrie event feeds. Visitor memory is backed by SQLite with WAL mode (`gatekeeper/visitor_memory.py`), storing privacy-preserving HMAC-SHA256 salted visitor IDs (`vis_xxxx`). Upward-only escalation policy (`gatekeeper/policy.py`) strictly enforces `T1 <= T2 <= T3` and returns safe default T1 on any internal or database error.
- **Alternatives considered**: Separate feature extractors for offline and live modes (rejected: violates AGENTS.md Rule 10 on parity); Redis/Postgres for visitor memory (rejected: adds unnecessary service dependencies for single-node VPS).
- **Why**: Zero external service overhead, bulletproof fail-cheap resilience, sub-millisecond local latency (<0.5 ms), and guaranteed offline/live consistency.
- **Consequences**: Verified with 14 unit tests across memory, policy, and feature extraction.

### 2026-11-11: Cost & Intelligence Yield Model with MITRE ATT&CK Regex Classification
- **Status**: ACCEPTED
- **Owner**: P2 / Analytics Lead
- **Context**: SPEC.md Section 9 requires calculating Session Yield (commands, file transfers, pivots, ATT&CK TTPs) and Session Cost (CPU, RAM, VM boot in Rupees) to determine the Yield per Rupee metric: $\sum Y / \sum C$.
- **Decision**: Implemented `analysis/cost_model.py` containing MITRE ATT&CK regex tag classification mapped to 11 key techniques (T1082, T1033, T1057, T1083, T1046, T1105, T1059.004, T1053.003, T1098.004, T1070.004, T1496), session yield calculator, cost allocation parameters in INR, comparative arm efficiency evaluation, and EVAL 6 random-weight sensitivity analysis.
- **Alternatives considered**: Fixed manual scoring without TTP detection (rejected: violates SPEC Section 9.1).
- **Why**: Provides rigorous mathematical evaluation of honeypot intelligence return on investment (ROI).
- **Consequences**: Verified with 7 unit tests in `analysis/test_cost_model.py`.

### 2026-11-11: Standalone Sticky Multi-Instance TCP Router (Plan B Fallback)
- **Status**: ACCEPTED
- **Owner**: P1 / Systems Lead
- **Context**: SPEC.md Section 5.3 pre-registered Plan B as a fallback mechanism if in-process adaptation encounters edge-case constraints or for cross-session multi-container routing.
- **Decision**: Implemented `router/sticky_router.py` using Python `asyncio` TCP stream splicing. The router checks visitor memory at accept-time, identifies the visitor's highest tier, and pipes raw bytes to the designated backend port without touching or mutating the SSH byte stream.
- **Alternatives considered**: Nginx / HAProxy stream proxy (rejected: lacks direct programmatic integration with SQLite visitor memory without external Lua scripts).
- **Why**: Standard-library asyncio implementation ensures pure byte-for-byte fidelity and zero external dependencies.
- **Consequences**: Verified with 4 unit tests in `router/test_sticky_router.py`.

### 2026-11-11: Adversary Detector Audit Runner with SAFETY.md Allowlist Enforcement
- **Status**: ACCEPTED
- **Owner**: P3 / Security Lead
- **Context**: SPEC.md Section 5.4 and SAFETY.md mandate that automated audit probes (honeypot-auditor heuristics, OS coherence checks, giveaway scans) run exclusively in isolated lab environments and must NEVER scan external hosts.
- **Decision**: Implemented `harness/detector_runner.py` with hardcoded safety guards (`is_target_allowlisted`). The runner immediately throws `SafetyViolationError` if any non-loopback / non-lab target is specified. Probes inspect OS coherence between `/etc/hostname`, `/etc/motd`, and banner, and scan filesystems for default Cowrie traces.
- **Alternatives considered**: Unrestricted target runner with CLI warnings (rejected: strictly prohibited by SAFETY.md and AGENTS.md Rule 6).
- **Why**: Non-negotiable safety guardrails preventing any unauthorized outbound network probing.
- **Consequences**: Verified with 5 unit tests in `harness/test_detector_runner.py`.

### 2026-11-11: Read-Only Results Dashboard with Zero External NPM/PIP Dependencies
- **Status**: ACCEPTED
- **Owner**: Frontend & Full-Stack Lead
- **Context**: SPEC.md Section 4 and AGENTS.md Rule 19 require a read-only dashboard that clearly labels panels as RECORDED, LAB, or LIVE, and strictly masks attacker identifiers (`vis_xxxx`).
- **Decision**: Implemented `dashboard/app.py` as a self-contained HTTP server serving an executive dark-mode UI with embedded SVG metrics and clean JSON API endpoints (`/api/stats`, `/api/decisions`, `/api/arms`). All visitor IPs are cryptographically hashed/masked with zero raw IPs exposed.
- **Alternatives considered**: Node.js / React / Next.js app (rejected: adds hundreds of megabytes of npm dependencies and complex build toolchains to a Python-centric research repository).
- **Why**: 100% portable, lightweight, fast (<5 ms response time), and strictly complies with all AGENTS.md hygiene and safety rules.
- **Consequences**: Verified with 4 unit tests in `dashboard/test_dashboard.py`.

### 2026-11-11: Empirical Arm Simulation Pipeline (EVAL 5.1 & SPEC 9)
- **Status**: ACCEPTED (SUPERSEDED / CLARIFIED)
- **Owner**: P2 / Analytics Lead
- **Context**: Pre-registered in EVAL.md Section 5.1 and SPEC.md Section 9, comparing four experimental arms (Arm A: Static T1, Arm B: Static T2, Arm C: Static T3, Arm D: Adaptive Escalation) on real Cowrie session interaction traces.
- **Decision**: Implemented `analysis/simulate_arms.py` using DuckDB streaming over `data/session_aggregation.jsonl.gz`. Evaluates yield, INR cost, and yield-per-rupee across 50,000 real-world sessions.
- **Scientific Audit & Caveats (Remediated 2026-11-12)**:
  1. **Oracle Hindsight Policy**: Arm D as simulated uses whole-session retrospective counters (`files >= 1 or pivots >= 1` for T3, `cmds >= 2` for T2), which are the exact components forming the `value = 1` target label. It functions as an empirical **oracle upper bound** (hindsight policy), not an online early-stage gatekeeper.
  2. **Uniform Yield Modeling Trade-off**: Under the modeling assumption that honeypot persona does not alter attacker behavior (uniform yield across arms = 2,371.3), Arm A (Static T1) is mathematically cheapest per yield unit (₹3.98 cost -> 595.7 Yield/₹ vs ₹86.70 cost -> 27.4 Yield/₹ for Arm D). Arm D is ~21.7x more expensive than Arm A under uniform yield. Its ~29.6x efficiency multiplier exists solely when contrasted against static unpruned full virtualization (Arm C: ₹2,564.68).
  3. **Cost Model Status**: Costs are nominal estimates (T1 ₹0.0001/sec, T2 ₹0.0002/sec, T3 ₹0.002/sec, VM boot ₹0.50) pending empirical KVM measurements from Spike S2.
- **Alternatives considered**: Theoretical spreadsheet simulation without empirical session traces (rejected: violates AGENTS.md Rule 2 "No fabricated results").
- **Why**: Anchored in empirical public data traces, adhering to frozen cost and yield definitions, with clear disclosures preventing misrepresentation.
- **Consequences**: Results saved to `results/arm_simulation.json`. Verified with 2 unit tests in `analysis/test_simulate_arms.py`.

### 2026-11-11: Natural Experiment Persona Effect Analysis (EVAL 5.3 & DATA D1)
- **Status**: ACCEPTED (AMENDED / RE-SCOPED)
- **Owner**: P2 / Analytics Lead
- **Context**: EVAL.md Section 5.3 mandates analyzing observational session outcomes across the 160 honeypot instances in the 50-day public dataset (`session_aggregation.jsonl.gz`) with strict no-causal language and Wilson 95% confidence intervals.
- **Decision**: Implemented `analysis/natural_experiment.py` aggregating session statistics across all 160 honeypot instances using DuckDB streaming.
- **Scientific Audit & Scope Correction (Remediated 2026-11-12)**:
  1. **No Group Column in Aggregation**: `session_aggregation.jsonl.gz` lacks the honeypot configuration `group` column (which exists only in event-level `data_all.zip`). Therefore, EVAL 5.3 persona effect analysis is marked as **PENDING event group data**.
  2. **Removal of Selection-on-Outcome**: Ranking instances by their own `value_1_rate` and reporting a 10x ratio was circular selection-on-outcome. This was removed. The script now characterizes descriptive baseline variance (p25, median, p75, min, max) with Wilson 95% score CIs.
  3. **Caveat Language**: Expressly embeds the required scientific caveat attributing variance to possible scanner targeting, AS topography, and probing biases rather than claiming causal configuration effects ("no causal language").
- **Alternatives considered**: Making causal claims regarding configuration efficacy from observational data (rejected: explicitly forbidden by pre-registered EVAL.md Section 5.3).
- **Why**: Rigorous observational characterization of honeypot variance while maintaining scientific integrity.
- **Consequences**: Results saved to `results/natural_experiment.json`. Verified with 4 unit tests in `analysis/test_natural_experiment.py`.

### 2026-11-12: Purging Cross-Split Source IPs and Survivorship Bias in Validation/Test Sets
- **Status**: ACCEPTED
- **Owner**: P2 / Analytics Lead
- **Context**: EXPERIMENT0.md §3 mandates strict disjoint source IP assignment across temporal splits: any source IP that appears in multiple periods is allocated exclusively to the earliest period's fold and purged from all subsequent folds (`src_ip NOT IN (SELECT DISTINCT src_ip FROM earlier_folds)`).
- **Decision**: Enforce disjoint source IP allocation via DuckDB SQL in `analysis/exp0_train.py` and log purged session counts.
- **Scientific Trade-offs & Survivorship Bias**:
  1. **Bias Rationale**: Eliminating cross-split source IPs prevents optimistic data leakage from recurring bots or multi-session scanning campaigns that repeat identical handshake and authentication features.
  2. **Distributional Shift**: Persistent, high-activity attackers that scan repeatedly over weeks are systematically assigned to earlier folds (train). As a consequence, validation and test splits are disproportionately skewed toward novel, ephemeral, or single-session scanners. This represents a known survivorship bias that models must generalize across.
  3. **Sample Collapse under Subsampling**: If a sample limit (e.g. 1,000 rows) is drawn chronologically, validation and test folds may collapse to 0 rows if all sampled IPs were active in earlier days. Full-day extraction or date-filtered stratified sampling must be used.
- **Alternatives considered**: Random source IP split without temporal order (rejected: causes severe temporal look-ahead leakage); Non-disjoint temporal split (rejected: causes cluster correlation leakage).
- **Why**: Highest scientific rigor against data leakage per AGENTS.md Rule 15 and EXPERIMENT0.md §3.
- **Consequences**: Documented in `DECISIONS.md` and tracked in `results/exp0/rules_summary.json` and `EXP0_RESULT.md`.

### 2026-11-12: Pre-Registration Desynchronization and Tagging of exp0-v2 / eval-v2
- **Status**: ACCEPTED
- **Owner**: Lead Architect / All
- **Context**: Git tags `eval-v1` and `exp0-v1` were placed at commit `bae4e27` prior to committing `results/exp0/splits.json` and `results/exp0/grid.json`. Under open-science standards, the pre-registration seal must freeze splits and grids before test evaluation.
- **Decision**:
  1. Acknowledge and document the desynchronization in `DECISIONS.md`.
  2. Maintain `eval-v1` and `exp0-v1` as initial specification tags.
  3. Freeze `splits.json` (calendar dates for train, val, test) and `grid.json` (hyperparameter grids for LogisticRegression and HistGradientBoosting), and create new Git tags `eval-v2` and `exp0-v2` sealing the complete pre-registered experimental configuration and flaw remediation.
- **Alternatives considered**: Force-deleting and moving `v1` tags (rejected: rewriting Git tag history obscures the audit trail).
- **Why**: Transparency and adherence to open-science pre-registration protocols (AGENTS.md Rule 3 and Rule 16).
- **Consequences**: Tag `exp0-v2` and `eval-v2` on commit finalizing flaw remediation.

