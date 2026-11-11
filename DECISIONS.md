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
