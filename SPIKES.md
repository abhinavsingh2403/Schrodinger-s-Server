# SPIKES.md: Go/No-Go Technical Spikes (S1 and S3 first; rest after Gate 0)

Version 0.2, 2026-11-11. A spike is a time-boxed investigation that answers one question and produces a written decision. Each spike writes its outcome to `SPIKE_RESULTS.md` (date, who, evidence, decision). **Gate 0 (v0.2):** only S1, S3 and Experiment 0 (`EXPERIMENT0.md`) are required first. S2, S4 and S5 run only if Gate 0 passes (S2 is needed only for the T3 tier, which is deferred). No feature work beyond the Gate 0 items before they are done. If a spike cannot be answered in its time box, record that as the result and take the stated fallback.

Time box guide: 1 working day each (S1 may take 2). S1 and S3 are blocking and, together with Experiment 0, form Gate 0. S2, S4 and S5 are deferred until Gate 0 passes.

---

## S1. Per-session persona / escalation in Cowrie (owner P1)

**Question.** Can Cowrie choose the persona (fake filesystem, command set, or backend) per session or per stage, from our own code, without a deep fork?

**Why.** Documentation describes backends (emulated shell, proxy, backend pool, experimental LLM) as configuration choices; per-session switching was not documented in what I found **[U]**.

**Steps**
1. Clone the pinned Cowrie release into `sensor/cowrie-src/` (read-only copy for study).
2. Read the code paths for: SSH transport setup and banner; key exchange logging; authentication and the point at which a login is accepted; creation of the shell protocol and loading of the fake filesystem; command dispatch; proxy/pool backend selection; the LLM backend. (Older public issue tracebacks mention files such as `src/cowrie/shell/protocol.py`, `src/cowrie/commands/base.py`, `src/cowrie/core/utils.py`, `src/twisted/plugins/cowrie_plugin.py` and `src/cowrie/pool_interface/*`; paths may have moved, so search rather than assuming.)
3. Write a throwaway proof of concept that, after successful login, selects between two different fake filesystems or two identities based on a trivial rule (for example, odd/even source port). Confirm that the second session actually sees the other persona.
4. Write down: the exact hook points, the lines of Cowrie that must change, whether an output plugin or a subclass suffices, and the risk of merge pain on upgrades.

**Acceptance.** A reproducible PoC showing per-session persona selection at login stage.
**Decision.**
- Achieved: use **Plan A** (in-process hook). Record the hook points in `DECISIONS.md`.
- Not achieved in the time box: use **Plan B** (sticky multi-instance routing by visitor memory). Update `README`/`SPEC` and the report wording: adaptation is cross-session only.

## S2. T3 feasibility, cost measurement and gatekeeper latency (owner P1)

**Questions.** (a) Does the chosen VPS expose hardware virtualization for QEMU/libvirt guests? (b) What are boot time, memory and CPU cost of a T3 session? (c) What is gatekeeper decision latency?

**Steps**
1. On the intended VPS, check for KVM (for example `/dev/kvm` and `kvm-ok` or the equivalent). If absent, record it; software emulation is expected to be slow **[U]**.
2. If KVM exists: set up Cowrie's backend pool per its documentation (`[proxy] backend = pool`, `[backend_pool] pool_only = false`, `pool = local`), with network filtering that blocks outbound Internet access from guests; keep proxy-to-pool traffic local because it is unencrypted. Note that connections are dropped until guests are ready.
3. Measure with a controlled load: N sessions per tier (T1, T2, T3) of scripted benign commands from the lab. Record per-session CPU seconds, GB-seconds, VM boot time, and idle cost of the always-on pool. Write the numbers to `results/cost_model.json` via a script.
4. Time the decision API with synthetic features (p50, p95).

**Acceptance.** A table of cost per tier and p95 decision latency, produced by a script.
**Decision.**
- KVM available and T3 works: keep T3 in the plan.
- KVM unavailable: use the SPEC 5.1 fallback ladder: (a) KVM-capable host; (b) proxy mode to a single resettable sandbox; (c) drop T3 and report as future work.
- p95 latency above 50 ms: decide at stages that tolerate it, or simplify models.

## S3. Data reality check and base rates (owner P2)

**Questions.** Do the files match the record-page schemas? What are the base rates of `value`? Is the companion repo usable and licensed for reuse?

**Steps**
1. Download `session_aggregation.jsonl.gz` only. Verify its MD5 against DATA.md and note any difference.
2. Load with DuckDB. Check that all 25 fields exist; count sessions, sessions with login success, sessions with commands, distribution of `cnt_command_input`, share with file transfers, share with direct-tcpip requests.
3. Compute the base rate of `value = 1` using the aggregate approximation (`cnt_command_input >= 5` or file transfer or pivot), overall and by day. Compare against the published one-shot observation from another deployment (147,752 of 148,850 non-interactive [S]); expect differences and write down why.
4. Download **two or three days** from `data_all.zip` (not the whole archive) to confirm event-level fields exist: `hassh`, `version`, `width`, `height`, `input`, `group`, `ts`.
5. Read the dataset's data descriptor (if published) and the companion repo README: how configurations were assigned to instances; the repo license; whether its configs are reusable.
6. Do not download `transferred_files.zip`.

**Acceptance.** `results/base_rates.json` and a one-page summary.
**Decision.**
- If the base rate of `value = 1` is extremely small or extremely large: revisit N_CMD **before `eval-v1` is tagged** and document it.
- If `group` is missing from the event data: the natural experiment in EVAL 5.3 must use instance-level configuration from the descriptor; if that is unavailable, drop 5.3.
- If the repo license forbids reuse: write our own T1/T2 configs and cite theirs as inspiration only.

## S4. Transport-layer detectability of Cowrie (owner P3)

**Question.** What does a third-party detector flag on a default Cowrie and on a hardened Cowrie, and can the server-side key-exchange algorithm list be changed to resemble OpenSSH?

**Steps**
1. Run the third-party detector (honeypot-auditor) against **our own lab** default Cowrie, using its authorization flag. Record version, flags used, per-category results, overall score. Run 3 times; note variance.
2. Repeat against a hardened lab Cowrie (custom filesystem, adjusted outputs).
3. Read Cowrie's SSH transport code to see whether the server's key-exchange/cipher/MAC preference lists are configurable. If yes, test whether changing them alters the detector's HASSH-related verdict.
4. Note which tells are protocol-level and cannot be fixed by persona changes.

**Acceptance.** A table of detector findings per configuration.
**Decision.** Fixes that are cheap go into T2. Residual tells are recorded and must appear in the report as limitations (SPEC R5).

## S5. How informative is HASSH and the early features? (owner P2)

**Question.** Do handshake features carry signal for `value`, or is HASSH too coarse? (A published clustering study found it too broad to correlate attacker IPs [S].)

**Steps**
1. On the two or three downloaded days, build a tiny logistic-regression and a tree model with handshake-only features versus handshake plus auth features. Use the group-by-source split from EVAL 3.
2. Record PR-AUC with CIs. This is a sanity check, not a result for the report.

**Acceptance.** A paragraph with numbers saying which feature groups appear useful.
**Decision.** If handshake-only is near random, plan on later stages (S3 to S5 in SPEC) and say so in the early-decision discussion.

---

## Spike results template (`SPIKE_RESULTS.md`)

```
### S<n> <title>
Date / owner:
What was done (commands, versions, commit):
Evidence (paths in results/ or logs):
Result:
Decision (Plan A/B, go/no-go, fallback taken):
What this changes in SPEC/EVAL:
```
