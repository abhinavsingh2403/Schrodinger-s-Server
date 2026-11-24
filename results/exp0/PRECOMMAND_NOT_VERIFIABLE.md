# S3 pre-command certification
Post-hoc exploratory. Verdict: NO for the audited archive.
| Audit count | Count |
|---|---:|
| Sampled days | 3 |
| Events with usable sensor, session and timestamp | 12380945 |
| Complete sessions with an identifiable first command | 184383 |
| session.params events tied with first command | 0 |
| Verified historical S3 decision boundaries | 0 |

The schema includes ts. The loader retains neither a verified per-session sequence nor a decision marker. File order and ts_indexed cannot establish callback order for tied timestamps.
The launcher requests S3 after ingesting session.params; the adapter also has a PTY hook. First command identifies a later cutoff. Neither proxy identifies the archive's actual S3 feature snapshot.
For future captures, record a masked session key, event type, event timestamp and monotonic session sequence on every event. At S3 feature capture record the same key, decision timestamp and last included sequence atomically with the feature snapshot.
Evidence: results/s3_event_schema.json and results/exp0/event_prefix_study.json. Model controls NOT RUN. Future evaluation requires a verified prefix ladder row and matching splits, then run `python -m analysis.posthoc_ml_eval --splits results/exp0`.
