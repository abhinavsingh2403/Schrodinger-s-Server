from pathlib import Path
import json
import pytest
from dashboard import evidence as api


def test_catalog_privacy_and_labels():
    index = api.response("/api/evidence/index")[1]
    assert {i["id"] for i in index["items"]} == set(api.CATALOG)
    for item in index["items"]:
        code, payload = api.evidence(item["id"])
        assert code == 200 and api.labels().keys() <= payload.keys()
        assert not api.PRIVATE.search(json.dumps(payload))
    assert api.response("/api/progress")[1]["data"] == json.loads((api.ROOT / "results/progress.json").read_text())


@pytest.mark.parametrize("key", ["../progress", "/progress", "%2e%2e", "C:/progress", "missing"])
def test_unlisted(key):
    assert api.evidence(key)[0] == 404


def test_unavailable(tmp_path, monkeypatch):
    path = tmp_path / "results/progress.json"
    assert api.evidence("progress", tmp_path)[1]["data"] is None
    path.parent.mkdir()
    path.write_text("{}")
    monkeypatch.setattr(api, "CAP", 1)
    assert api.evidence("progress", tmp_path)[0] == 404


def test_escape(tmp_path):
    root = tmp_path / "repo"
    (root / "results").mkdir(parents=True)
    outside = tmp_path / "private"
    outside.write_text("{}")
    try:
        (root / "results/progress.json").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")
    assert api.evidence("progress", root)[0] == 404
