# Viva Examination Preparation: 30 Questions & Answers

Canonical examiner questions and verified answers for project defense.
Every response is grounded in code, data, or registered audit findings.

---

## Group 1: Problem Definition & Motivation

### Q1: What specific problem in modern honeypot research does Schrödinger's Server address?
Internet-facing honeypots face over 99% automated scanner noise and under 1% interactive attackers. Indiscriminately serving high-interaction deception wastes massive compute resources on shallow probes. This project introduces early triage to optimize intelligence yield per rupee spent [README.md, SPEC.md §1].

### Q2: What is the core hypothesis or central thesis of this project?
The hypothesis is that a lightweight gatekeeper can infer early in an SSH session (handshake, auth, or first command) whether an attacker is likely to yield high-value interactive intelligence, escalating promising sessions while serving cheap emulation to noise [SPEC.md §1, README.md].

### Q3: Why is "yield per rupee" chosen as the primary metric rather than raw recall or accuracy?
In practical cyber defense, compute budgets are finite. A high-interaction honeypot that catches every attacker but exhausts its hosting budget on day one is operationally unviable. Yield per rupee mathematically formalizes the trade-off between intelligence gain and infrastructure cost [SPEC.md §9, README.md].

### Q4: How is attacker utility or "value" defined in your problem formulation?
A session is labeled high-value (Value=1) if the visitor executes multiple shell commands, downloads or uploads files, or establishes an interactive PTY session beyond trivial one-shot scanning [SPEC.md §3, results/base_rates.json].

### Q5: What are the defined fidelity tiers in your architecture?
Tier T1 Lite is a low-interaction shell with minimal resource cost; Tier T2 Hardened introduces custom fake filesystem overlays and command persistence; Tier T3 Real VM uses proxying to real sandboxed Linux virtual machine guests (deferred in current scope) [SPEC.md §3, docs/ARCHITECTURE.md].

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
Per EXPERIMENT0.md, a learned model must beat the best pre-declared baseline rule by at least 5% absolute recall at a 10% escalation budget, with a Bonferroni-adjusted confidence interval strictly greater than zero [EXPERIMENT0.md §12, results/exp0/AUDIT.md].

### Q12: What were the results at Stage S1 (Handshake)?
At S1, simple baseline rules matched or outperformed learned ML models (ML recall 0.0572 vs rule recall 0.0970), indicating that pre-auth cryptographic negotiation does not reliably discriminate attacker intent [results/exp0/table.csv, results/exp0/AUDIT.md].

### Q13: What were the results at Stage S2 (Authentication)?
At S2, baseline rule R1 (login success) captured the bulk of positive sessions (0.5632 recall vs 0.5497 ML recall); machine learning did not provide a statistically significant advantage over simple rules [results/exp0/table.csv, results/exp0/AUDIT.md].

### Q14: What was the result at Stage S3 (Session Setup), and what is the mechanical verdict?
At S3, Logistic Regression reported a recall of 0.2919 versus 0.1151 for baseline rule R6, yielding a +17.68 percentage point gain with an adjusted confidence interval of [+0.0052, +0.6125], mechanically triggering a PASS-ML verdict [results/exp0/table.csv, results/exp0/AUDIT.md].

### Q15: Why is the Stage S3 finding classified as exploratory rather than confirmatory?
Sensitivity audits revealed that transfer-labelled sessions dominate the gain, a shuffled-label sanity diagnostic fails near-budget expectations, and event-chronology checks remain unverified. It cannot be claimed as a validated pre-command causal signal [results/exp0/AUDIT.md].

---

## Group 4: System Architecture & Gatekeeper Implementation

### Q16: How does the Gatekeeper service operate in the running deployment?
The Gatekeeper runs as a standalone Python HTTP microservice exposing REST endpoints (/health, /decide, /record_session) on port 5000, querying visitor history and applying classification models within milliseconds [gatekeeper/decision_api.py, docs/ARCHITECTURE.md].

### Q17: How is visitor privacy protected without losing tracking capability?
Source IPs are cryptographically hashed using salted HMAC-SHA256 upon arrival to generate masked visitor identifiers (vis_xxxx). Raw IP addresses are never stored in the database or exposed on dashboard endpoints [gatekeeper/visitor_memory.py, AGENTS.md Rule 6].

### Q18: What is the "fail-cheap" principle in your Gatekeeper design?
If the Gatekeeper service encounters an internal error, corrupted model, or network timeout, the honeypot defaults safely to Tier T1 Lite rather than dropping the connection or raising an uncaught exception [gatekeeper/decision_api.py, SPEC.md §5.2].

### Q19: How is identical identity maintained across tiers to prevent fingerprinting?
The system enforces a shared identity profile (srv-app-01, Ubuntu 22.04 LTS, OpenSSH 8.9p1) across both T1 and T2 configurations, ensuring that an escalated session does not reveal contradictory OS banners or kernel strings [config/identity.yaml, infra/cowrie.cfg].

### Q20: What is the difference between Plan A and Plan B escalation mechanisms?
Plan A uses an in-process Twisted Conch adapter hook inside Cowrie to switch environments dynamically during a session. Plan B is a fallback multi-instance TCP front-end that splices connections across instances between sessions [SPEC.md §5.3, sensor/adaptive_server.py].

---

## Group 5: Safety, Operational Hygiene & Reproducibility

### Q21: What safety restrictions are enforced regarding honeypot network egress?
Outbound network connections from the honeypot or sandboxed containers are strictly forbidden by firewall rules and internal Docker bridge configurations to prevent attackers from using the lab as an exploit pivot [SAFETY.md §2, infra/smoke_test.ps1].

### Q22: How does the repository guard against fabricated numbers in reports and UI?
Per AGENTS.md Rule 2 and truthfulness tests, no numerical results are hand-typed. All dashboard figures, status checklists, and Gate 0 tables are generated by deterministic Python scripts reading from results/*.json [dashboard/test_truthfulness.py, analysis/render_status.py].

### Q23: How do the Kali adversary scripts ensure safety during live demonstrations?
The attacker scripts (bot_like, transfer_like, interactive) incorporate an allowlist safety guard that inspects the destination IP and refuses execution against any host other than 127.0.0.1, localhost, or private RFC 1918 subnets [harness/attackers/common.py, SAFETY.md].

### Q24: What is the purpose of the Docker smoke test script?
The smoke test verifies that docker-compose.yml defines an internal isolated bridge network, publishes ports strictly to 127.0.0.1, and refuses to bind services to 0.0.0.0 without an explicit allowlist entry [infra/smoke_test.ps1, infra/smoke_test.sh].

### Q25: How is offline/live feature parity verified?
A dedicated parity test suite feeds identical session features through both the offline training pipeline and the live Gatekeeper engine, verifying that model predictions match within strict floating-point tolerances [gatekeeper/test_model_inference_parity.py].

---

## Group 6: Limitations, Threats to Validity & Future Work

### Q26: What is the current verified progress percentage of the project?
The project stands at a weighted completion of 40.0% based on the objective 14-item evidence rubric, with core data pipelines and Gatekeeper models built while live deployment trials remain pending [docs/STATUS.md, results/exp0/progress.json].

### Q27: Why was Tier T3 (Real VM) deferred in the current implementation?
Tier T3 requires hardware nested virtualization (KVM) or heavy QEMU guest pools, which impose severe hosting costs and are typically unavailable on standard cloud VPS instances [SPEC.md §0, SPEC.md §5.1].

### Q28: What is the limitation of the Arm D (Adaptive) simulation results?
Arm D in arm_simulation.json represents a theoretical oracle retrospective hindsight upper bound that assumes complete post-hoc knowledge of session yield, rather than an unconstrained real-world deployment measurement [results/arm_simulation.json, HANDOFF.md].

### Q29: What is the status of third-party detector evaluation (EVAL H4)?
Third-party detector evaluation using external automated tools (such as honeypot-auditor) is NOT YET EVALUATED; in-repo test suites currently check only internal heuristic consistency [harness/detector_runner.py, HANDOFF.md].

### Q30: What are the three most critical engineering steps needed to achieve a 9+/10 system?
First, execute full end-to-end Cowrie event forwarding to Gatekeeper in live Linux containers. Second, validate event-level prefix chronologies on raw data. Third, run a multi-hour live Kali attack demonstration showing dynamic T1 to T2 escalation [results/exp0/AUDIT.md, HANDOFF.md].
