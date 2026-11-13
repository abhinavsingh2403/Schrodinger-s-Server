# Slide Deck Outline: Schrödinger's Server

Presentation outline for project viva and technical defense.
Every bullet cites its primary supporting source document.

---

### Slide 1: The SSH Deception Problem
- Internet-facing honeypots face over 99% automated scanner noise and under 1% interactive attackers [README.md].
- Unconditional high-interaction deception wastes massive compute and financial budget on shallow bots [README.md].

### Slide 2: Core Thesis & Objectives
- An early-session gatekeeper can infer interactive intent before expensive personas are instantiated [SPEC.md, README.md].
- The primary optimization goal is maximizing intelligence yield per rupee under strict resource budgets [SPEC.md, README.md].

### Slide 3: System Architecture
- Modular stack: Cowrie SSH sensor, in-process Conch lifecycle adapter, and SQLite WAL Gatekeeper [docs/ARCHITECTURE.md, SPEC.md].
- Monotone upward escalation with uniform cross-tier identity profiles to prevent attacker fingerprinting [docs/ARCHITECTURE.md, SPEC.md].

### Slide 4: Experimental Methodology & Data
- Evaluated on a 52-day multi-instance Cowrie public dataset partitioned into train, validation, and test splits [DATA.md, results/exp0/AUDIT.md].
- Strict cross-split source IP purging applied to prevent botnet identity leakage across temporal sets [DATA.md, results/exp0/AUDIT.md].

### Slide 5: Gate 0 Pre-Registered Protocol
- Pre-declared test evaluates whether learned models beat simple rules by 5% recall at a 10% escalation budget [EXPERIMENT0.md, DECISIONS.md].
- Mandates Bonferroni-adjusted confidence intervals strictly above zero for a conclusive pass [EXPERIMENT0.md, DECISIONS.md].

### Slide 6: Gate 0 Empirical Results
- Early stages S1 and S2 showed rules matching or exceeding ML classifiers [results/exp0/AUDIT.md, results/exp0/table.csv].
- Stage S3 reported ML recall of 0.2919 versus baseline rule recall of 0.1151 [results/exp0/AUDIT.md, results/exp0/table.csv].

### Slide 7: Scientific Audit & Sensitivity Caveats
- S3 advantage is exploratory: driven predominantly by transfer-labelled sessions and aggregate counter proxies [results/exp0/AUDIT.md].
- Shuffled-label diagnostics and full event-chronology prefix checks remain unresolved [results/exp0/AUDIT.md].

### Slide 8: Resource Economics & Simulation Arms
- Empirical comparison of static baselines (Arm A, Arm B) against adaptive gatekeeping [results/arm_simulation.json, README.md].
- Arm D represents an oracle retrospective upper bound rather than an unconstrained real-time claim [results/arm_simulation.json, README.md].

### Slide 9: Project Maturity & Verification Status
- Verified weighted completion of 40.0% derived from an objective evidence-based rubric [docs/STATUS.md, results/exp0/progress.json].
- Core ML loading, REST API, truthfulness tests, and safety allowlists are fully built and tested [docs/STATUS.md, README.md].

### Slide 10: Limitations & Future Milestones
- High-interaction real VM execution (Tier T3) and live randomized field trials are deferred [SPEC.md, results/exp0/AUDIT.md].
- Event-level command prefix resolution and verified Linux Cowrie deployment remain key next steps [results/exp0/AUDIT.md, docs/STATUS.md].
