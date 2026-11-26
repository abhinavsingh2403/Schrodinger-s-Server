# Viva Examination Preparation: 30 Questions & Answers

Canonical examiner questions and verified answers for project defense.
Every response is grounded in code, data, or registered audit findings.

---

## Group 1: Problem Definition & Motivation

### Q1: What specific problem in modern honeypot research does SchrÃ¶dinger's Server address?
Can early session evidence guide escalation within a fixed budget? This is the research question. (SPEC.md)

### Q2: What is the core hypothesis or central thesis of this project?
The hypothesis is that a lightweight gatekeeper can infer early in an SSH session (handshake, auth, or first command) whether an attacker is likely to yield high-value interactive intelligence, escalating promising sessions while serving cheap emulation to noise [SPEC.md Â§1, README.md].

### Q3: Is cost reduction proven?
Cost reduction remains unproven. CPU ranges overlapped across repeats. The recorded memory difference was small. Both personas ran inside one sensor process, and PTY use differed between workloads. (results/cost/COST_PER_TIER.md)

### Q4: How is attacker utility or "value" defined in your problem formulation?
The whole-session label uses distinct command count, file transfer or direct-tcpip activity. PTY allocation alone does not establish the label. Aggregate analyses use a proxy. (EXPERIMENT0.md)

### Q5: What are the defined fidelity tiers in your architecture?
T1 and T2 are in-process shell personas. T2 exposes additional decoy content. T3 remains a proposed guest tier. (sensor/adaptive_server.py)

---

## Group 2: Dataset & Preprocessing

### Q6: What dataset was used for training and evaluating Experiment 0?
The project utilizes a 52-day multi-instance public Cowrie dataset comprising over 38 million recorded sessions, with 5,292,235 sessions across the partitioned training, validation, and test splits [results/base_rates.json, results/exp0/AUDIT.md].

### Q7: What is the empirical base rate of high-value sessions in the dataset?
Across the 38.1 million recorded sessions, only 1,232,570 sessions (3.23%) exhibited high-value activity under the Value=1 aggregate approximation criteria [results/base_rates.json].

### Q8: How were dataset splits partitioned to prevent data leakage?
Splits are partitioned chronologically into training, validation, and test sets. Furthermore, disjoint source-IP purging was executed to eliminate cross-split recurring scanner botnets from contaminating the test set [results/exp0/AUDIT.md, analysis/exp0_train.py].

### Q9: Why was `session_aggregation.jsonl.gz` used instead of raw packet captures?
The 1.3 GB session aggregation file contains pre-aggregated event counters per session, allowing rapid training and statistical bootstrapping across millions of sessions without the 19.4 GB storage overhead of unindexed event streams [analysis/README.md, DATA.md].

### Q10: What limitation does aggregate session data impose on evaluating command stages?
Aggregate session counters record whole-session counts rather than timestamped event chronologies. Consequently, command stages S4 and S5 are honestly reported as NOT EVALUABLE on aggregate data [results/exp0/AUDIT.md, docs/STATUS.md].

---

## Group 3: Gate 0 Evaluation & Statistical Findings

### Q11: What was the pre-registered Gate 0 evaluation criteria?
Per EXPERIMENT0.md, a learned model must beat the best pre-declared baseline rule by at least 5% absolute recall at a 10% escalation budget, with a Bonferroni-adjusted confidence interval strictly greater than zero [EXPERIMENT0.md Â§12, results/exp0/AUDIT.md].

### Q12: What were the results at Stage S1 (Handshake)?
The S1 rule captured more labelled positives than the fitted scorer at the registered budget. The label measures observed activity. (results/exp0/table.csv)

### Q13: What were the results at Stage S2 (Authentication)?
At S2, baseline rule R1 (login success) captured the bulk of positive sessions (0.5632 recall vs 0.5497 ML recall); machine learning did not provide a statistically significant advantage over simple rules [results/exp0/table.csv, results/exp0/AUDIT.md].

### Q14: What was the result at Stage S3 (Session Setup), and what is the mechanical verdict?
S3 cleared the original mechanical gate. Post-hoc controls leave the learned advantage unconfirmed. (results/exp0/POSTHOC_ML_EVAL.md)

### Q15: Why is the Stage S3 finding classified as exploratory rather than confirmatory?
Why did ML fail to establish an advantage? A constant-label fit still ranked sessions by an activity counter. In Experiment 1, shuffled labels retained apparent performance at S2 and S4. Learned, shuffled and feature-sum scorers selected the same S4 cutoff decisions (results/exp1/ROOT_CAUSE.md). (results/exp0/NULL_ROOT_CAUSE.md)

---

## Group 4: System Architecture & Gatekeeper Implementation

### Q16: How does the Gatekeeper service operate in the running deployment?
The HTTP service exposes health, decision and session-recording endpoints. The stored S3 model is PurePythonLogisticRegression (models/model_s3.json). The R7-labelled runtime fallback returns a constant. LAB_DEMO_NOT_ML uses declared demo rules. (gatekeeper/decision_api.py)

### Q17: How is visitor privacy protected without losing tracking capability?
Source IPs are cryptographically hashed using salted HMAC-SHA256 upon arrival to generate masked visitor identifiers (vis_xxxx). Raw IP addresses are never stored in the database or exposed on dashboard endpoints [gatekeeper/visitor_memory.py, AGENTS.md Rule 6].

### Q18: What is the "fail-cheap" principle in your Gatekeeper design?
The service provides a fail-cheap decision fallback. Round-trip latency can exceed the sensor deadline (results/cost/concurrency_probe.json). (gatekeeper/decision_api.py)

### Q19: How is identical identity maintained across tiers to prevent fingerprinting?
The system enforces a shared identity profile (srv-app-01, Debian 12 Bookworm, OpenSSH 9.2p1) across both T1 and T2 configurations, ensuring that an escalated session does not reveal contradictory OS banners or kernel strings [config/identity.yaml, infra/cowrie.cfg].

### Q20: What is the difference between Plan A and Plan B escalation mechanisms?
Plan A uses an in-process Twisted Conch adapter hook inside Cowrie to switch environments dynamically during a session. Plan B is a fallback multi-instance TCP front-end that splices connections across instances between sessions [SPEC.md Â§5.3, sensor/adaptive_server.py].

---

## Group 5: Safety, Operational Hygiene & Reproducibility

### Q21: What safety restrictions are enforced regarding honeypot network egress?
Docker demonstrates internal service isolation and edge-only loopback publishing. Direct-IP and named egress attempts failed in the recorded sensor check. The edge merges visitor addresses, so the multi-visitor demonstration uses native WSL. (HANDOFF.md)

### Q22: How does the repository guard against fabricated numbers in reports and UI?
Dashboard tests exercise provenance, missing data and database-derived metrics. (dashboard/test_truthfulness.py)

### Q23: How do the Kali adversary scripts ensure safety during live demonstrations?
The attacker scripts (bot_like, transfer_like, interactive) incorporate an allowlist safety guard that inspects the destination IP and refuses execution against any host other than 127.0.0.1, localhost, or private RFC 1918 subnets [harness/attackers/common.py, SAFETY.md].

### Q24: What is the purpose of the Docker smoke test script?
Infra tests check network membership and loopback publication on the edge. (infra/test_infra_configs.py)

### Q25: How is offline/live feature parity verified?
A dedicated parity test suite feeds identical session features through both the offline training pipeline and the live Gatekeeper engine, verifying that model predictions match within strict floating-point tolerances [gatekeeper/test_model_inference_parity.py].

---

## Group 6: Limitations, Threats to Validity & Future Work

### Q26: What is the current verified progress percentage of the project?
Use the generated percentage and checklist in docs/STATUS.md. (results/progress.json)

### Q27: Why was Tier T3 (Real VM) deferred in the current implementation?
The T3 guest is deferred. There is no implemented guest tier to evaluate. (SPEC.md)

### Q28: What is the limitation of the Arm D (Adaptive) simulation results?
Arm D in arm_simulation.json represents a theoretical oracle retrospective hindsight upper bound that assumes complete post-hoc knowledge of session yield, rather than an unconstrained real-world deployment measurement [results/arm_simulation.json, HANDOFF.md].

### Q29: What is the status of third-party detector evaluation (EVAL H4)?
H4 remains INCONCLUSIVE. The recorded handshake observations cannot distinguish authenticated personas. (results/detector/DETECTOR_RESULT.md)

### Q30: What are the three most critical engineering steps needed to achieve a 9+/10 system?
The prefix logger and study protocol exist. Human participation, T3 and the public trial remain outstanding (HANDOFF.md). Replay verified input receipt only (results/replay/REPLAY_RESULT.md). (docs/EVENT_LOG.md)
