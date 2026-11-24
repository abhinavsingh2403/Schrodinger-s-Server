"""Check sequence isolation, privacy and fail-open logging."""
import json
from sensor.prefix_log import PrefixLog


def test_prefix(tmp_path):
    path = tmp_path/"events"
    log = PrefixLog(path)
    for sid in ("session-A","session-B","session-A"):
        log.append(sid,event="cowrie.session.params")
    log.append("session-A",stage="S3",features={"cnt_session_params":2})
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["seq"] for r in rows[:3]] == [1,1,2]
    assert rows[-1]["last_seq"] == rows[2]["seq"]
    assert rows[0]["session"] == rows[-1]["session"] != rows[1]["session"]
    assert "session-A" not in path.read_text()


def test_off_and_failure(tmp_path):
    PrefixLog(None).append("s",event="connect")
    assert not list(tmp_path.iterdir())
    log = PrefixLog(tmp_path)
    log.append("s",event="connect")
    assert log.path is None
