# Experiment 1 feasibility
Post-hoc probe, not part of the pre-registered gate.

Local audited members: 3; compressed bytes: 1159435421; events: 12380945. First day stream and boundary check: 29.33 seconds (digest check excluded).
Full ZIP in the cache: no. Source: DATA.md, data_all.zip.
Archive fields present: ts=yes, sensor=yes, session=yes, eventid=yes, input=yes, src_ip=yes. Command text is available and hashed in memory.

| Stage | Reached | Tied | Tie rate | Identifiable (untied) | Future outcome unresolved | Future positive | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| S1 | NA | NA | NA | 0 | NA | NA | NOT IDENTIFIABLE |
| S2 | 2018682 | 0 | 0.0000% | 2018682 | 2018682 | 59793 | IDENTIFIABLE |
| S3 | NA | NA | NA | 0 | NA | NA | NOT IDENTIFIABLE |
| S4 | 184383 | 0 | 0.0000% | 184383 | 184091 | 48949 | IDENTIFIABLE |
| S5 | 17160 | 0 | 0.0000% | 17160 | 8596 | 8288 | IDENTIFIABLE |

S1 uses the runtime NEWKEYS hook. The archived client algorithm offer cannot date completion. S3 uses the previously recorded zero in PRECOMMAND_NOT_VERIFIABLE.md.
S2 uses first auth outcome per session. S4 and S5 use the first and third command events (SPEC and the existing offline audit; the live adapter also calls S5 on command two). A tie means any other event at the same timestamp in that session. Only complete same-day sessions with untied anchors enter the unresolved and future-positive counts. The outcome is five distinct commands, transfer or direct-TCPIP.

FEASIBLE FOR stages [S2, S4, S5]. Laptop CPU: yes for these cached members, processed one at a time. Full archive runtime unmeasured. Before fitting, register endpoint definitions, preserve session grouping, and check chronological/source-disjoint splits. Capture explicit S1/S3 markers for those stages.

Reproduce: `python -m analysis.experiment1_feasibility --cache data/event_prefix_study`.
