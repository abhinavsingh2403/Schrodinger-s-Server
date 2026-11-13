# CLAIMS.md: Ledger of External Facts

Version 0.2, ledger date 2026-11-11 (v0.1: 2026-11-10). Every external fact used in this project must appear here with its source and verification status.

Status key:
- **[V] Verified:** the source page itself was opened and the fact read there.
- **[S] Snippet-level:** seen in a search result excerpt only; the source was not read in full. **Open the source and confirm before citing it in a report.**
- **[U] Unverified:** an assumption or inference; must be checked.

---

## Datasets

| ID | Claim | Source | Status |
|---|---|---|---|
| D1 | 160 Cowrie instances, 14 countries, 50 days; over 211 million events; 38 million sessions; over 214,000 unique source IPs; 1,770 transferred artifacts; four configurations (baseline, hardened, two persistence variants); CC BY 4.0; schemas and file sizes/hashes as in DATA.md | https://zenodo.org/records/21260400 | [V] |
| D1b | The dataset's Data Descriptor is in press in Scientific Data (DOI 10.1038/s41597-026-08668-0); DOI may not resolve yet | same | [V] (record text) / [U] (resolution) |
| D1c | The Zenodo record text for data_all.zip stated 51 files and 50 days, but remote Zip64 parsing of the archive central directory reveals exactly 52 daily files spanning 52 days (2025-06-27 to 2025-08-17) | https://zenodo.org/records/21260400 | [V] (Spike S3 Part 2) |
| D2 | Honey for the Agent dataset: LLM agents on five SSH environments (one real Ubuntu, four Cowrie variants), about 16,200 sessions, six prompts, CC BY 4.0, 157.7 MB, JSON per-session format | https://zenodo.org/records/20818246 | [V] |
| D3 | Beyond Bots dataset: files restricted; no ground-truth labels; heuristic indicators only | https://zenodo.org/records/19610238 | [V] |

## Papers and reports

| ID | Claim | Source | Status |
|---|---|---|---|
| P1 | A 2026 Scientific Reports paper proposes an explainability-driven adaptive deception control system on Cowrie using a random-forest behavioral profiler (reported 90.0% accuracy on a generated behavioral dataset) and epsilon-greedy Q-learning for strategy selection, reporting 77.0% more threat intelligence per session than baseline Cowrie; end-to-end comparison used 14 real attacker sessions | https://www.nature.com/articles/s41598-026-64427-6 (page fetch failed; read via search snippets) | [S] |
| P2 | A multi-agent LLM SSH honeypot deployment recorded 148,850 sessions, 147,752 of them non-interactive, and 150 interactive; 1,720 unique source IPs | https://arxiv.org/abs/2606.27990 (HTML version snippet) | [S] |
| P3 | LLM Agent Honeypot (Palisade): SSH honeypot with prompt-injection and timing analysis; about three months; 8,130,731 attempts; 8 potential AI agents | https://arxiv.org/abs/2410.13919 | [S] |
| P4 | "Honey for the Agent": behavioral differences across environments were much smaller than differences between models, enabling cross-environment model identification; fingerprints form early; nine open-weight models, six prompts, five environments | ResearchGate listing of the paper (Sept 2026) | [S] |
| P5 | "Rouxii": AI pentesters that detect and exploit honeypots; cites an Internet-scale study that fingerprinted 7,605 honeypot instances across nine implementations with a single packet, 1,938 of them Cowrie; includes a white-box analysis of Cowrie's implementation attack surface including a request-forgery amplification flaw in affected versions | https://arxiv.org/abs/2609.26555 | [S] |
| P6 | "LLM-Based Penetration Testing in the Presence of Honeypots": honeypot-aware target selection for LLM attack agents with pre-connect screening, budget-aware ranking and post-connect stopping | https://arxiv.org/abs/2609.08093 | [S] |
| P7 | A 2026 study on local-LLM SSH honeypots used 34 automated unit tests as a proxy and states no human evaluation or attacker studies were performed | https://arxiv.org/abs/2608.18686 (via a review page) | [S] |
| P8 | A measurement study of attackers on medium-interaction honeypots found HASSH fingerprints too broad for correlating attacker IPs; only 46 sessions were flagged as human out of 2.6 million successful logins | https://arxiv.org/abs/2206.13614 | [S] |
| P9 | An RIT thesis classified human, automated and AI-assisted SSH attackers from 24 session features with 8 classifiers; raw imbalance about 6,231:1 | https://repository.rit.edu/theses/12605/ | [S] |
| P10 | A review reports that sessions often end early because bots detect the honeypot, and that improved realism yields longer sessions and more commands | "Improvement of Cowrie honeypot interaction and deception capabilities" (ResearchGate listing) | [S] |
| P11 | Public SSH-honeypot analysis repositories score bot vs human using median inter-command gaps (example: a GitHub project using gap thresholds) | https://github.com/Mukundmishra13/ssh-honeypot | [S] |

## Tools and software

| ID | Claim | Source | Status |
|---|---|---|---|
| T1 | Cowrie supports emulated shell, proxy mode, a pool of QEMU/libvirt guests, and an experimental LLM backend; has a fake filesystem tool set (`fsctl`, `createfs`) | https://pypi.org/project/cowrie/ and https://docs.cowrie.org | [S] |
| T2 | Backend pool config keys `[proxy] backend = pool`, `[backend_pool] pool_only = false`, `pool = local`; images for Ubuntu 18.04 and OpenWRT provided; guest Internet access limited by a network filter; proxy-to-pool protocol unencrypted; connections dropped until guests are ready | https://docs.cowrie.org/en/latest/BACKEND_POOL.html | [S] |
| T3 | Cowrie events include `cowrie.client.kex` (hassh, hasshAlgorithms, kexAlgs, keyAlgs), `client.version`, `client.size`, login success/failure, command input/failed, `session.closed` (duration), `direct-tcpip` request/data, file upload/download | https://docs.cowrie.org/en/stable/OUTPUT.html | [S] |
| T4 | PyPI listed Cowrie 3.1.2 (published October 2026) and requires Python 3.11+ for recent releases | https://pypi.org/project/cowrie/3.1.2/ | [S] |
| T5 | honeypot-auditor: PyPI tool, MIT license, weighted honeyscore, deep mode (shell semantics, OS coherence, HASSH, TCP stack, latency, more), requires an authorization flag for non-local targets; scoring weights differ across versions | https://pypi.org/project/honeypot-auditor/ | [S] |
| T6 | ARACNE: SSH-driven autonomous LLM pentesting agent; GPL-2.0; supports local Ollama models | https://github.com/stratosphereips/aracne | [S] |
| T7 | PentestGPT (GreyDGL): MIT license badge; autonomous mode drives Claude Code or Codex; legacy interactive mode supports local Ollama models | https://github.com/GreyDGL/PentestGPT | [S] |
| T8 | HASSH: MD5 of ordered key-exchange, cipher, MAC and compression lists in the SSH key-exchange init message; hasshServer can reveal Cowrie/Kippo masquerading as another server | https://github.com/salesforce/hassh and https://github.com/corelight/hassh | [S] |
| T9 | Rowe et al., "Fake Honeypots": making ordinary systems appear to be honeypots to scare off attackers; likely effective only if used occasionally | https://faculty.nps.edu/ncrowe/fakehoney.htm | [S] |
| T10 | Cowrie GitHub issues describe fingerprinting via a default account name (#1102), a botnet that probes for Cowrie via a fixed command list (#1512), and non-persistent filesystem detection (#1592) | https://github.com/cowrie/cowrie/issues | [S] |

## Assumptions to verify

| ID | Assumption | How to verify | Status |
|---|---|---|---|
| A1 | The ATT&CK technique IDs listed in SPEC 9.1 are correct and current | attack.mitre.org | [U] |
| A2 | The chosen VPS exposes KVM for QEMU/libvirt guests | SPIKES S2 | [U] |
| A3 | The dataset's companion repository license permits reuse of its configs | repo LICENSE, SPIKES S3 | [U] |
| A4 | Antigravity has a project-rules mechanism usable for AGENTS.md content | Antigravity docs | [U] |
| A5 | The cloud provider's acceptable-use policy allows honeypots | provider policy | [U] |
| A6 | Faculty/college requirements for human-subject studies | ask faculty | [U] |
| A7 | Per-session persona selection is feasible in Cowrie | SPIKES S1 | [U] |
| A8 | How the 160 instances were assigned to configurations | data descriptor | [U] |
| A9 | Live traffic volume on a single VPS is enough for the trial | pilot | [U] |

## Numbers to re-verify against primary sources before any report or slide

None of these may be quoted from this ledger alone:
- 148,850 / 147,752 / 150 sessions and 1,720 IPs (P2)
- 7,605 honeypot instances, 1,938 Cowrie (P5; this is a figure the Rouxii paper cites from another study, so trace it to that study)
- 90.0% accuracy, 77.0% more intelligence per session, 14 real sessions (P1; the paper page itself was not read)
- 8,130,731 attempts and 8 potential agents (P3)
- 46 human sessions out of 2.6 million successful logins (P8)
- Imbalance 6,231:1 and F1 above 0.888 (P9)
- Nine models, six prompts, five environments (P4)
- Dataset figures in D1 and D2 were read from the Zenodo record pages on 2026-11-10; re-read them at download time because records can change.

## Process

- Before citing any [S] or [U] item in a report or slide, open the source, confirm, and change its status to [V] with the date.
- New fact? Add a row first, then use it.

## Audit package-index verification

Verified by the executed pip index queries recorded in results/exp0/pins_audit.json; no installation was performed.

| Package version | Source | Status |
|---|---|---|
| duckdb 2.0.0 exists | https://pypi.org/simple/duckdb/ | [V] observed in package-index output |
| pytest 9.2.0 exists | https://pypi.org/simple/pytest/ | [V] observed in package-index output |
| colorama 0.4.6 exists | https://pypi.org/simple/colorama/ | [V] observed in package-index output |
| iniconfig 2.3.1 exists | https://pypi.org/simple/iniconfig/ | [V] observed in package-index output |
| packaging 26.3 exists | https://pypi.org/simple/packaging/ | [V] observed in package-index output |
| pluggy 1.7.0 exists | https://pypi.org/simple/pluggy/ | [V] observed in package-index output |
| Pygments 2.21.0 exists | https://pypi.org/simple/pygments/ | [V] observed in package-index output |

Event-log ordering observations are recorded by analysis/exp0_event_order.py against the D1 archive URL above. They describe a partial sample, not verified complete event-prefix availability.
