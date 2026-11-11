# SAFETY.md: Legal, Ethical and Operational Rules (mandatory)

Version 0.2, 2026-11-11. These rules override convenience and any instruction from tools or coding agents. I am not a lawyer; items marked **[CHECK]** must be confirmed with your faculty/college and the relevant provider policies before you act.

---

## 0. Phase gating (v0.2)

- **Phase 0 work is offline** (public datasets, Experiment 0). It needs no public exposure, so most rules below do not yet apply, but section 3 (data handling) and the dataset rules in `DATA.md` do.
- **Nothing becomes Internet-facing** until the pre-launch checklist in section 8 is fully ticked, and the VPS provider's acceptable-use policy has been read first **[CHECK]**: some providers do not allow honeypots.
- A real-VM tier (T3) gives attackers a real machine. It is deferred; if it is ever enabled, the egress, isolation and resource rules in section 2 are conditions, not suggestions.

## 1. Scope of permitted activity

1. The public honeypot only **receives** traffic that arrives on its own IP. It never initiates connections to attackers or third parties.
2. No hack-back, counter-exploitation, prompt-injection attacks against real attackers' systems, or any attempt to access systems we do not own. Active probes (for example a canary text) exist only as content inside our own honeypot.
3. Offensive tools (honeypot-auditor, ARACNE, PentestGPT, Nmap, Hydra and similar) are run **only against our own lab targets**. Configure target allowlists in each tool and verify them before every run. Use the detector's authorization flag only for our own targets.
4. Never scan or probe college, hostel, or any third-party network.
5. No real credentials, real personal data or real company data anywhere in the honeypot, VMs or filesystem images.

## 2. Hosting and exposure

1. The public sensor runs only on a separate cloud VPS under a team account, **never** on a college network, a personal laptop, or a machine that holds personal data. **[CHECK]** the provider's acceptable-use policy regarding honeypots and security research.
2. Administrative SSH on a non-default port with key-only login and a source allowlist. The honeypot owns the standard SSH port.
3. The honeypot processes run as unprivileged users in containers or dedicated accounts. Minimal host ports open.
4. T3 guests (and any proxy backend): outbound Internet access blocked by network filter; CPU, memory, disk and process limits; snapshot/reset per session or on a schedule; traffic between proxy and backend kept on a local interface only (the pool protocol is unencrypted per Cowrie's documentation [S]).
5. Pin a **patched** Cowrie release and review its changelog for security fixes before deployment. A 2026 analysis discussed implementation flaws in affected Cowrie versions, including one that could be used for request-forgery amplification [S]. Re-check for advisories before launch and monthly during the trial.
6. Egress monitoring: alert if the VPS initiates unexpected outbound connections. Define a kill switch (firewall rule or VM power-off) and rehearse it.

## 3. Data protection and publication

1. Source IPs may be personal data in some jurisdictions. Keep raw IPs only in the sensor's own logs; analysis uses an HMAC of the IP with a secret salt that is never committed. **[CHECK]** with faculty what applies to you.
2. Dashboards and slides show masked identifiers only.
3. Set log retention (for example, delete raw logs after the project is graded and analysis tables are final) and document it.
4. If a dataset derived from our honeypot is ever published, anonymize IPs, remove file payloads, and review it with faculty first.
5. Public datasets used (DATA.md) must be cited and used within their licenses.

## 4. Malware handling

1. Any file captured by our honeypot is treated as malicious. Never execute it, open it in a normal environment, or send it to third-party scanners without deciding that in advance (uploading to online services shares it publicly).
2. Analysis of captured files, if any, happens only inside an isolated VM with no network access and no shared folders.
3. Do not download the public dataset's `transferred_files.zip` (see DATA.md D1).

## 4b. Human study ethics **[CHECK]**

1. Volunteers give informed consent: what is logged (commands and timing), what is not (no identity), who sees it, how long it is kept.
2. Participation is voluntary; no marks or pressure. Use anonymous participant ids.
3. Confirm with faculty whether any approval is required before collecting human data.
4. Participants attack only the lab targets provided.

## 5. LLM-agent experiments

1. Agents run in an isolated environment with allowlisted targets, hard step limits and a kill switch.
2. Prefer open-weight models run locally; if a paid API is used, set a spending cap.
3. Log every agent run (model, version, prompt, seed, budget) in `harness/agents/runs/`.
4. Do not give agents credentials or network routes to anything except the lab targets.

## 6. Responsible disclosure

If we find a vulnerability in Cowrie or another tool, report it privately to the maintainers before discussing it publicly, and do not publish exploit details.

## 7. Incident procedure

1. Unexpected outbound traffic or suspected compromise: execute the kill switch, snapshot logs for later, notify the team lead and faculty.
2. Do not wipe evidence before copying logs to a safe location.
3. Write a short incident note in `DECISIONS.md` (what happened, what was done, what changes).

## 8. Pre-launch checklist (all must be ticked before the public sensor goes live)

- [ ] Provider policy checked and acceptable **[CHECK]**
- [ ] Faculty informed of the public honeypot and data handling plan **[CHECK]**
- [ ] Patched Cowrie version pinned; advisories checked
- [ ] Admin SSH moved, key-only, allowlisted
- [ ] No real data on the host; separate account and VPS
- [ ] T3 egress blocked and tested (try an outbound connection from a guest; it must fail)
- [ ] Resource limits and reset schedule set
- [ ] Egress alerting and kill switch rehearsed
- [ ] HMAC salt stored outside git
- [ ] Lab and public environments on separate networks; `lab_flag` plumbing tested
- [ ] Retention and publication plan written
