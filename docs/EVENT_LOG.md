# Sensor prefix evidence

Set SENSOR_PREFIX_LOG to a private, writable JSONL file before starting the native launcher. Use one file per sensor process. The default is off. The launcher appends each row on its reactor thread. A write failure disables further logging for that process.

Event rows contain session (per-process salted HMAC), event (Cowrie event type), event_time (upstream timestamp when supplied), observed_at (UTC sensor clock), and seq (per-session order). No commands, credentials or addresses are copied. A marker is one JSON line containing session, stage, observed_at, last_seq and the numeric features supplied to the gatekeeper. It records a request even if the gatekeeper subsequently times out.

Example marker shape (placeholders): `{"session":"<masked>","stage":"S3","observed_at":"<UTC>","last_seq":<event sequence>,"features":{<numeric snapshot>}}`.

Audit the recorded model counters at the boundary with `python -m analysis.marker_consistency` in the pinned native WSL lab environment. Discard truncated or incomplete logs.
