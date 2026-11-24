# Sensor prefix evidence

Set SENSOR_PREFIX_LOG to a private, writable JSONL file before starting the native launcher. Use one file per sensor process. The default is off. The launcher appends each row on its reactor thread. A write failure disables further logging for that process.

Event rows contain session (per-process salted HMAC), event (Cowrie event type), event_time (upstream timestamp when supplied), observed_at (UTC sensor clock), and seq (per-session order). No commands, credentials or addresses are copied. A marker is one JSON line containing session, stage, observed_at, last_seq and the numeric features supplied to the gatekeeper. It records a request even if the gatekeeper subsequently times out.

Example marker shape (placeholders): `{"session":"<masked>","stage":"S3","observed_at":"<UTC>","last_seq":<event sequence>,"features":{<numeric snapshot>}}`.

Audit the recorded model counters at the boundary with `python -m analysis.marker_consistency` in the pinned native WSL lab environment. Discard truncated or incomplete logs.

For a synthetic train/test pair, run `python -m analysis.marker_consistency --capture train.jsonl` then repeat with `--capture test.jsonl` in the native lab. Each command starts fresh services. Script labels are bot (negative) and interactive or transfer (positive). Slow recon is excluded. Multiple SSH connections from one script are related observations.
Evaluate with `python -m analysis.prefix_s3_eval --train train.jsonl --test test.jsonl --output results/study/PREFIX_S3_EVAL.md`.
Human-study evaluation is NOT RUN. Supply independent participant-disjoint captures using this schema, adding the independently assigned binary outcome as label on S3 markers. Run `python -m analysis.prefix_s3_eval --human-study --train human-train.jsonl --test human-test.jsonl --output human-prefix-report.md`.
In the repeated bot workload the two unmarked connections closed before session.params. Neither had an S3 decision in SQLite. The coverage check now joins the session records with a fresh private SENSOR_PREFIX_JOIN_KEY shared by the analysis and sensor, and reports early closes separately from missing requested markers.
