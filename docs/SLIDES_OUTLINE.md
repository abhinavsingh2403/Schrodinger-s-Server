# Slide Deck Outline: Schrödinger's Server

Presentation outline for project viva and technical defense.
Every bullet cites its primary supporting source document.

---

### Slide 1: The SSH Deception Problem
- Describe the distribution of observed session activity in D1. (results/base_rates.json)
- Introduce the fixed escalation budget. (SPEC.md)

### Slide 2: Core Thesis & Objectives
- Early intent prediction remains an open question. (results/exp1/EXPERIMENT1_RESULT.md)
- Present resource measurements and the limits of the workload comparison. (results/cost/COST_PER_TIER.md)

### Slide 3: System Architecture
- Modular stack: Cowrie SSH sensor, in-process Conch lifecycle adapter, and SQLite WAL Gatekeeper [docs/ARCHITECTURE.md, SPEC.md].
- T1 and T2 share a configured identity. H4 remains inconclusive. (config/identity.yaml, results/detector/DETECTOR_RESULT.md)

### Slide 4: Experimental Methodology & Data
- The aggregate corpus spans the recorded days in results/base_rates.json. Gate 0 used a sampled day split, with source purging and its survivorship limitation (results/exp0/splits.json, results/exp0/AUDIT.md).
- Strict cross-split source IP purging applied to prevent botnet identity leakage across temporal sets [DATA.md, results/exp0/AUDIT.md].

### Slide 5: Gate 0 Pre-Registered Protocol
- Pre-declared test evaluates whether learned models beat simple rules by absolute recall difference at the declared threshold in EXPERIMENT0.md at a 10% escalation budget [EXPERIMENT0.md, DECISIONS.md].
- Mandates Bonferroni-adjusted confidence intervals strictly above zero for a conclusive pass [EXPERIMENT0.md, DECISIONS.md].

### Slide 6: Gate 0 Empirical Results
- Early stages S1 and S2 showed rules matching or exceeding ML classifiers [results/exp0/AUDIT.md, results/exp0/table.csv].
- Stage S3 reported ML recall of 0.2919 versus baseline rule recall of 0.1151 [results/exp0/AUDIT.md, results/exp0/table.csv].

### Slide 7: Scientific Audit & Sensitivity Caveats
- S3 advantage is exploratory: driven predominantly by transfer-labelled sessions and aggregate counter proxies [results/exp0/AUDIT.md].
- Activity-based rankings survived label controls. (results/exp0/NULL_ROOT_CAUSE.md)

### Slide 8: Resource Economics & Simulation Arms
- Identify the arms as retrospective simulations. (results/arm_simulation.json)
- Arm D represents an oracle retrospective upper bound rather than an unconstrained real-time claim [results/arm_simulation.json, README.md].

### Slide 9: Project Maturity & Verification Status
- Show the current weighted checklist. (results/progress.json)
- Tests exercise model loading, API responses, provenance and lab target restrictions (gatekeeper/test_model_inference_parity.py, gatekeeper/test_decision_api.py, dashboard/test_truthfulness.py, harness/attackers/test_source_ip.py).

### Slide 10: Limitations & Future Milestones
- High-interaction real VM execution (Tier T3) and live randomized field trials are deferred [SPEC.md, results/exp0/AUDIT.md].
- The prefix logger exists. The participant study remains outstanding. (docs/EVENT_LOG.md)
