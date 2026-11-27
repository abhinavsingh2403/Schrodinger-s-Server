# Viva Examination Preparation: 30 Questions & Answers

Canonical examiner questions and verified answers for project defense.
Every response is grounded in code, data, or registered audit findings.

---

## Group 1: Problem Definition & Motivation

### Q1: What specific problem in modern honeypot research does Schrödinger's Server address?
Can early session evidence guide escalation within a fixed budget? This is the research question. (SPEC.md)

### Q2: What is the core hypothesis or central thesis of this project?
The hypothesis is that a lightweight gatekeeper can infer early in an SSH session (handshake, auth, or first command) whether an attacker is likely to yield high-value interactive intelligence, escalating promising sessions while serving cheap emulation to noise [SPEC.md §1, README.md].

### Q3: Is cost reduction proven?
Cost reduction remains unproven. CPU ranges overlapped across repeats. The recorded memory difference was small. Both personas ran inside one sensor process, and PTY use differed between workloads. (results/cost/COST_PER_TIER.md)

### Q4: How is attacker utility or "value" defined in your problem formulation?
The whole-session label uses distinct command count, file transfer or direct-tcpip activity. PTY allocation alone does not establish the label. Aggregate analyses use a proxy. (EXPERIMENT0.md)

### Q5: What are the defined fidelity tiers in your architecture?
T1 and T2 are in-process shell personas. T2 exposes additional decoy content. T3 remains a proposed guest tier. (sensor/adaptive_server.py)

---

## Group 2: Dataset & Preprocessing

### Q6: What dataset was used for training and evaluating Experiment 0?
Experiment 0 sampled days from the public multi-instance Cowrie corpus. The frozen split file identifies the days used for each partition (DATA.md, results/exp0/splits.json).

### Q7: What is the empirical base rate of high-value sessions in the dataset?
Across the 38.1 million recorded sessions, only 1,232,570 sessions (3.23%) exhibited high-value activity under the Value=1 aggregate approximation criteria [results/base_rates.json].

### Q8: How were dataset splits partitioned to prevent data leakage?
The chronological split purges overlapping source addresses. Different addresses may still represent related activity (results/exp0/AUDIT.md).

### Q9: Why was `session_aggregation.jsonl.gz` used instead of raw packet captures?
Each aggregate row supplies whole-session event counters. Those counters support aggregate proxy labels but cannot reconstruct the order of commands (DATA.md, EXPERIMENT0.md).

### Q10: What limitation does aggregate session data impose on evaluating command stages?
Aggregate session counters record whole-session counts rather than timestamped event chronologies. Consequently, command stages S4 and S5 are honestly reported as NOT EVALUABLE on aggregate data [results/exp0/AUDIT.md, docs/STATUS.md].

---

## Group 3: Gate 0 Evaluation & Statistical Findings

### Q11: What was the pre-registered Gate 0 evaluation criteria?
The gate requires an absolute recall improvement of at least five percentage points at the ten-percent budget, a positive adjusted lower confidence bound and the minimum positive sample size (EXPERIMENT0.md, section 12).

### Q12: What were the results at Stage S1 (Handshake)?
The S1 rule captured more labelled positives than the fitted scorer at the registered budget. The label measures observed activity. (results/exp0/table.csv)

### Q13: What were the results at Stage S2 (Authentication)?
The validation-selected rule was R7_decision_tree. Its test recall was 0.5609, compared with 0.5477 for the learned scorer (results/exp0/table.csv, EXPERIMENT0.md).

### Q14: What was the result at Stage S3 (Session Setup), and what is the mechanical verdict?
S3 cleared the original mechanical gate. Post-hoc controls leave the learned advantage unconfirmed. (results/exp0/POSTHOC_ML_EVAL.md)

### Q15: Why did the learned scorer fail to establish an advantage?
A constant-label fit still ranked sessions by an activity counter. In Experiment 1, shuffled labels retained apparent performance at S2 and S4. Learned, shuffled and feature-sum scorers selected the same S4 cutoff decisions (results/exp1/ROOT_CAUSE.md). (results/exp0/NULL_ROOT_CAUSE.md)

---

## Group 4: System Architecture & Gatekeeper Implementation

### Q16: How does the Gatekeeper service operate in the running deployment?
The HTTP service exposes health, decision and session-recording endpoints. The stored S3 model is PurePythonLogisticRegression (models/model_s3.json). The R7-labelled runtime fallback returns a constant. LAB_DEMO_NOT_ML uses declared demo rules. (gatekeeper/decision_api.py)

### Q17: How is visitor privacy protected without losing tracking capability?
Visitor memory derives HMAC-SHA256 identifiers using a supplied salt or VISITOR_SALT. Its development fallback is public, so secrecy requires a configured salt. The decision-log insert stores the derived identifier. Dashboard responses apply a separate deterministic SHA-256 mask by default (gatekeeper/visitor_memory.py, gatekeeper/decision_api.py, dashboard/decision_views.py). Sensor logs may contain raw addresses (DATA.md).

### Q18: What is the "fail-cheap" principle in your Gatekeeper design?
The service provides a fail-cheap decision fallback. Round-trip latency can exceed the sensor deadline (results/cost/concurrency_probe.json). (gatekeeper/decision_api.py)

### Q19: How is identity configuration shared across tiers?
T1 and T2 read the shared identity configuration. Launcher tests compare Cowrie overrides with those values. This checks configuration consistency. Detectability remains inconclusive (config/identity.yaml, sensor/run_sensor.py, gatekeeper/test_launcher_identity.py, results/detector/DETECTOR_RESULT.md).

### Q20: What is the difference between Plan A and Plan B escalation mechanisms?
Plan A switches the in-process persona through the Cowrie adapter. Plan B is the alternative routing design in the specification. This answer describes the implemented adapter and the proposed alternative (sensor/adaptive_server.py, SPEC.md).

---

## Group 5: Safety, Operational Hygiene & Reproducibility

### Q21: What safety restrictions are enforced regarding honeypot network egress?
Docker demonstrates internal service isolation and edge-only loopback publishing. Direct-IP and named egress attempts failed in the recorded sensor check. The edge merges visitor addresses, so the multi-visitor demonstration uses native WSL. (HANDOFF.md)

### Q22: How does the repository guard against fabricated numbers in reports and UI?
Tests check for random updates, literal session arrays and selected copied base-rate values, and exercise provenance and unavailable data. These are specific regression checks (dashboard/test_truthfulness.py).

### Q23: How do the Kali adversary scripts ensure safety during live demonstrations?
The shared destination guard delegates to the detector harness allowlist. A separate source-address validator accepts IPv4 loopback bindings. These guardrails are exercised by tests (harness/attackers/common.py, harness/detector_runner.py, harness/attackers/test_source_ip.py).

### Q24: Which Docker network settings do the infrastructure tests check?
Infra tests check network membership and loopback publication on the edge. (infra/test_infra_configs.py)

### Q25: How is offline/live feature parity verified?
The scoring tests compare feature vectors and predictions on fixture inputs. Captured-row parity has separate coverage. This establishes parity for the exercised inputs (gatekeeper/test_model_inference_parity.py, gatekeeper/test_real_row_parity.py).

---

## Group 6: Limitations, Threats to Validity & Future Work

### Q26: What is the current verified progress percentage of the project?
Read the generated weighted checklist in docs/STATUS.md and results/progress.json. Its percentage accounts for implementation milestones. Predictive evidence is reported separately in the experiment reports (analysis/progress_accounting.py, results/exp1/EXPERIMENT1_RESULT.md).

### Q27: Why was Tier T3 (Real VM) deferred in the current implementation?
The T3 guest is deferred. There is no implemented guest tier to evaluate. (SPEC.md)

### Q28: What can the saved oracle simulation establish?
The saved arm analysis labels itself a simulated oracle and uses nominal resource assumptions. It cannot establish deployment costs or economic benefit (results/arm_simulation.json, analysis/simulate_arms.py).

### Q29: What is the status of third-party detector evaluation (EVAL H4)?
H4 remains INCONCLUSIVE. The recorded handshake observations cannot distinguish authenticated personas. (results/detector/DETECTOR_RESULT.md)

### Q30: Which evaluations and capabilities remain outstanding?
Human-study execution, the persona-effect study, a T3 guest and the public trial remain outstanding. Replay currently demonstrates input receipt. Further evaluation needs explicit outcomes and controls (docs/EVENT_LOG.md, docs/STUDY_PROTOCOL.md, HANDOFF.md, results/replay/REPLAY_RESULT.md).
