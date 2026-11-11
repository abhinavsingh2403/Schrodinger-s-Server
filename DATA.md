# DATA.md: Datasets

Version 0.2, 2026-11-11. Status tags: **[V]** = read from the Zenodo record page on 2026-11-10; **[S]** = seen only in a search snippet; **[U]** = unverified. We have **not opened or downloaded any data file yet**; field availability inside the files must be confirmed in SPIKES S3.

Integrity: record page hashes below are as shown on the record pages at read time. A record can be modified later (the 160-instance record shows a modification date of 2026-11-05); recompute and compare hashes after download, and note any mismatch in `DECISIONS.md`.

---

## D1. Deployment of 160 Cowrie SSH honeypot instances across four distinct configurations (primary dataset)

| Item | Value |
|---|---|
| Record | https://zenodo.org/records/21260400 (DOI 10.5281/zenodo.21260400) [V] |
| Authors | Mikuláš, Krajčík, Helebrandt, Kotuliak (Slovak University of Technology in Bratislava) [V] |
| Citation requested | A Data Descriptor "Deployment of 160 Cowrie SSH honeypot instances across four distinct configurations", Scientific Data, DOI 10.1038/s41597-026-08668-0, listed as in press when read; cite it once it is published, and check that the DOI resolves [V] |
| License | CC BY 4.0 [V] |
| Scale | 50 continuous days; 160 Cowrie instances in 14 countries; over 211 million event records; 38 million SSH sessions; over 214,000 unique source IPs; 1,770 unique transferred file artifacts deduplicated by SHA-256 [V] |
| Configurations | Four, run in parallel: default Baseline; Enhanced hardened; two persistence-enabled (per-user and global filesystem state) [V] |
| Companion code | https://github.com/matusmikulas/COW160x4_dataset (ingestion for ELK/ClickHouse, example usage, honeypot configurations). License: **[U], check before copying anything** |
| IP anonymization | Source and honeypot IPs are anonymized [V] |

Files and hashes shown on the record page [V]:

| File | Size | MD5 |
|---|---|---|
| `data_all.zip` (51 files, one per day) | 19.4 GB | 5b6d6e77e5f7247ac400d2318cef7adb |
| `session_aggregation.jsonl.gz` | 1.3 GB | 1f3897650fb420c97c14ff452398c3f8 |
| `transferred_files.zip` | 8.0 GB | 1099a06827c9e426c6ac10e102e747d0 |
| `transferred_files_metadata.csv` | 367.1 kB | 120ae0da9518d96fbe245ef8dcebb2fb |
| `malformed.txt` | 14.6 kB | d60148e631fe4f042ff4d5f0eb59451e |

**`session_aggregation.jsonl.gz` schema [V]** (25 fields): `session, src_ip, honeypot_ip, first_seen, last_seen, total_events, cnt_client_fingerprint, cnt_client_kex, cnt_client_size, cnt_client_var, cnt_client_version, cnt_command_failed, cnt_command_input, cnt_command_success, cnt_direct_tcpip_data, cnt_direct_tcpip_request, cnt_file_download, cnt_file_download_failed, cnt_file_upload, cnt_log_closed, cnt_login_failed, cnt_login_success, cnt_session_closed, cnt_session_connect, cnt_session_params`.
Not in this file: hassh, client version string, command text, inter-event timing, honeypot configuration group. Those live in event-level `data_all`.

**`data_all.zip` event schema [V]** (57 fields, selected): `ts` (UTC, microsecond), `eventid`, `session`, `sensor`, `group` (Cowrie configuration group), `arch`, `hassh`, `hasshAlgorithms`, `kexAlgs`, `keyAlgs`, `encCS`, `macCS`, `compCS`, `langCS`, `version` (SSH client banner), `width`, `height`, `input` (command), `duration`, `username`, `password`, `url`, `destfile`, `shasum`, `filename`, `outfile`, `dst_ip`, `dst_port`, `src_ip`, `src_port`, plus GeoIP/ASN fields for source and honeypot.

**Intended use here**
1. Base rates and the offline Model V study (EVAL 5.1) using `session_aggregation` for scale and a few days of `data_all` for event-level features.
2. Natural experiment on persona effect (EVAL 5.3) using the `group` field and per-instance configuration.
3. Real botnet command traces for the replay adversary (event-level `input` per session), kept held-out from tuning.

**Known limits and cautions**
- No attacker-type labels (bot/human/agent). Do not invent them; use outcome labels (EVAL 2.1).
- Configuration assignment across instances/regions may be confounded **[U]**; read the data descriptor.
- `transferred_files.zip` contains potentially malicious payloads (the record warns they are packaged in password-protected archives). **We do not need it. Do not download or open it** unless a specific, approved analysis requires it, and then only inside an isolated, execution-restricted environment [V].
- Counting `cnt_command_input` counts input events, not distinct commands.
- The aggregation file's size (1.3 GB compressed) is workable with DuckDB on a laptop; the full event-level archive is not; use day subsets.

## D2. Honey for the Agent: Cyber Deception and Behavioral Fingerprinting of LLM-Based Attackers (agent logs)

| Item | Value |
|---|---|
| Record | https://zenodo.org/records/20818246 (DOI 10.5281/zenodo.20818246) [V] |
| Authors | Maddaloni, Safargalieva (data curators); Vasilomanolakis (supervisor); Technical University of Denmark [V] |
| License | CC BY 4.0 [V] |
| Content | Interaction logs of LLMs acting as autonomous SSH shell operators on five environments: one real Ubuntu server and four Cowrie variants; about 16,200 session files; each experimental cell has 30 sessions; six system prompts; maximum 20 or 30 turns per session [V] |
| Models | The associated paper reports nine open-weight models and six attacker prompts across five environments [S: ResearchGate abstract snippet] |
| Files | `Logs_final.zip` 157.7 MB (md5 4f3b30538e6e4c492716f87f184dd816); `inputs.json` 4.6 kB (md5 293fbf2b4944f9449ff04ef1564af00e) [V] |
| Layout | `Logs_final/prompt_N/{20|30}/environment/model/sessionNN.json` [V] |
| Session format | Turn 0 = [system prompt, start timestamp] and [banner, connection latency ms]; later turns = [LLM raw output, response time ms], [shell output, execution time ms], [raw command, parsed command] [V] |
| Reported findings (from the paper snippet) | Behavioral differences across environments were much smaller than differences between models; fingerprints form early in the interaction [S] |

**Intended use:** external test set and leave-one-model/leave-one-prompt-out analysis for Model A; command-style features. **Not** the sole source of agent positives for the deployed detector (shortcut risk, SPEC 7.2).

**Known limits:** a different harness and log format from live Cowrie logs; capped turns (20 or 30); agent prompts instruct reconnaissance, deception detection or exploitation, which may not match real attacker prompts; no negative (non-agent) sessions.

## D3. Beyond Bots: Identifying Human-Driven SSH Intrusions in the Wild (**NOT USED**)

- https://zenodo.org/records/19610238 (CC BY 4.0). The record page showed files as **restricted** and states the dataset has **no ground-truth labels**; its behavioral indicators are heuristics only [V].
- Decision: not used for training or labels. It may be cited as related work only. (An earlier planning note suggested using it as a human-label source; that was wrong.)

## D4. Optional small datasets (not required)

- Kaggle "Medium-interaction SSH honeypot data" (CC0, two weeks on an Azure server, includes Cowrie database, JSON logs and TTY logs) [S]. Useful only for early pipeline testing.
- Zenodo "A 4-month dataset of interactive SSH honeypot logs and command payloads" (145,425 events, 28 interactive sessions from 7 actors) [S]. Too small for modelling.

## D5. Data we will generate ourselves

| Data | Where | Purpose | Notes |
|---|---|---|---|
| Lab agent sessions (ARACNE, PentestGPT, at least 4 open-weight models) | Lab sensor | Model A positives and cross-source tests | Same Cowrie JSON format as negatives; tag `lab_flag = 1` |
| Replay bot sessions | Lab sensor | Model A negatives; replay adversary | Held-out traces for evaluation |
| Human volunteer sessions | Lab sensor | Model A negatives; blind-test results | Consent; anonymous ids only |
| Live public-VPS logs | Public sensor | Live trial | Raw IPs stay only in sensor logs; hashed in analysis |

## Data handling rules

1. Raw data stays out of git (`data/` is gitignored). Commit only hashes and download scripts.
2. Record every download date, URL, file hash and comparison with the record-page hash in `data/README.md`.
3. Treat source IPs as potentially personal data in anything shared or published: hash or aggregate them; never publish raw IPs from our own VPS.
4. Never execute anything extracted from captured payloads outside an isolated VM.
5. Cite datasets exactly as the record pages request; keep a `CITATIONS.bib` file.
