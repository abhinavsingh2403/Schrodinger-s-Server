"""Unit tests for harness/demo/populate_demo_db.py (synthetic probe generator)."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from harness.demo.populate_demo_db import populate_synthetic_decisions


def test_populate_synthetic_decisions(tmp_path: Path) -> None:
    """Verifies that populate_synthetic_decisions generates scripted probe decisions for pipeline testing."""
    db_file = tmp_path / "test_gk.db"

    total = populate_synthetic_decisions(db_path=str(db_file), reset=True)
    assert total == 9

    # Verify directly from SQLite
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM decision_log ORDER BY id ASC").fetchall()
    conn.close()

    assert len(rows) == 9

    # Verify all generated rows carry explicit SYNTHETIC provenance
    for r in rows:
        assert r["provenance"] == "SYNTHETIC"

    # Verify synthetic bot probe session stays at T1
    bot_rows = [r for r in rows if r["session_id"] == "sess_synth_bot_01"]
    assert len(bot_rows) == 2
    for r in bot_rows:
        assert r["tier_decided"] == "T1"

    # Verify synthetic interactive probe escalates to T2
    int_rows = [r for r in rows if r["session_id"] == "sess_synth_int_02"]
    assert len(int_rows) == 4
    # S1 is T1, S2, S3, S4 are T2
    assert int_rows[0]["tier_decided"] == "T1"
    assert int_rows[1]["tier_decided"] == "T2"
    assert int_rows[2]["tier_decided"] == "T2"
    assert int_rows[3]["tier_decided"] == "T2"
