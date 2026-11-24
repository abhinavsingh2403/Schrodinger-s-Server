# Lab participant protocol

Participation is voluntary. You can quit at any time by typing exit or disconnecting. The lab records commands and timestamps, and the sensor records event types and numeric decision snapshots. We use a participant code and masked session IDs for analysis. Please enter only lab commands and fake values. Do not supply personal data, private file contents or real credentials. The coordinator keeps raw Cowrie logs and the decision database private. Ask questions and consent before connecting.

Use only the loopback lab. Assign consecutive codes starting with P01. Give each participant all three instructions in an independently shuffled order (shuffle three cards before each participant). Run one participant and one instruction at a time. Record the assignment before login. Use the fake login root/password. Enter the password at the prompt.

| Instruction | Participant action |
|---|---|
| A | Open a real terminal, run `ssh -tt -p 2222 root@127.0.0.1`, explore the emulated host, then exit. |
| B | Run one command without a PTY: `ssh -T -p 2222 root@127.0.0.1 hostname`. |
| C | Open one terminal session, inspect the hostname and directory listing, and pause between commands before exiting. |

Before starting the native launcher, use a fresh private shell and working directory. Set `umask 077`, `export SENSOR_PREFIX_JOIN_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"` and `export SENSOR_PREFIX_LOG="$PWD/events.jsonl"`. Keep this shell for export. Use a dedicated empty decision database. For each connection reaching S3 copy its masked session value from the new S3 marker into labels.csv with header `participant_code,instruction,session_hint`. Record early disconnects separately. Avoid overlapping sessions and never commit study inputs, keys or participant exports.

Run `python -m analysis.study_export --events events.jsonl --db decisions.db --labels labels.csv --output results/study/study_sessions.csv`. Supply fresh output paths. Then run `python -m analysis.prefix_s3_eval --study-export results/study/study_sessions.csv --output human-prefix-report.md`. Odd participant codes train and even codes test. Both partitions need both labels. A/C versus B represents assigned instruction. Collect human consent and outcomes before interpreting the study.
