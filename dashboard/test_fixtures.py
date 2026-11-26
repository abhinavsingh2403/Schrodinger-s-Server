"""Check shipped examples retain their endpoint envelopes and privacy guarantees."""
import json
from pathlib import Path
from dashboard.app import LEGACY
from dashboard.evidence import CATALOG, PRIVATE

def test_fixture_coverage():
    directory = Path(__file__).with_name("fixtures")
    expected = set(LEGACY) | {"empty_summary", "unknown_session", "session", "summary", "index", "progress"}
    expected.update("evidence_" + key for key in CATALOG)
    assert {p.stem for p in directory.glob("*.json")} == expected
    for name in expected:
        example = json.loads((directory / (name + ".json")).read_text(encoding="utf8"))
        assert example["generated_from_commit"] and example["generated_by"] == "dashboard.make_fixtures"
        assert not PRIVATE.search(json.dumps(example["response"]))
