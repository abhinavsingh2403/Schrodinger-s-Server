"""Check backup contents and overwrite protection."""
import sqlite3
import pytest
from harness.demo.showcase import keep_database


def test_snapshot(tmp_path):
    source, backup = tmp_path / "source.db", tmp_path / "saved.db"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE sample(value)")
        db.execute("INSERT INTO sample VALUES (42)")
    backup.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        keep_database(source, backup)
    assert backup.read_bytes() == b"existing"
    keep_database(source, backup, force=True)
    with sqlite3.connect(backup) as db:
        assert db.execute("SELECT value FROM sample").fetchone() == (42,)
