"""
Unit tests for gatekeeper visitor memory and HMAC visitor ID derivation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from gatekeeper.visitor_memory import (
    VisitorMemory,
    derive_visitor_id,
    get_masked_id,
)


def test_hmac_derivation_deterministic() -> None:
    salt = b"test-salt-secret-001"
    id1 = derive_visitor_id("192.168.1.100", salt)
    id2 = derive_visitor_id("192.168.1.100", salt)
    id_other_ip = derive_visitor_id("192.168.1.101", salt)
    id_other_salt = derive_visitor_id("192.168.1.100", b"different-salt")

    assert id1 == id2
    assert id1 != id_other_ip
    assert id1 != id_other_salt
    assert len(id1) == 16


def test_masked_id_format() -> None:
    masked = get_masked_id("10.0.0.5", b"test-salt")
    assert masked.startswith("vis_")
    assert len(masked) == 12


def test_visitor_memory_lifecycle(tmp_path: Path) -> None:
    db_file = tmp_path / "visitors.db"
    vm = VisitorMemory(db_file, salt=b"lifecycle-salt")

    # Initial unknown visitor
    v0 = vm.get_visitor("1.2.3.4")
    assert v0["n_sessions"] == 0
    assert v0["highest_tier_served"] == "T1"

    # First session: T1
    v1 = vm.record_session("1.2.3.4", tier_served="T1")
    assert v1["n_sessions"] == 1
    assert v1["highest_tier_served"] == "T1"

    # Second session: escalated to T2
    v2 = vm.record_session("1.2.3.4", tier_served="T2", value_label=1)
    assert v2["n_sessions"] == 2
    assert v2["highest_tier_served"] == "T2"
    assert v2["last_value_label"] == 1

    # Third session: served T1, but highest_tier_served MUST remain T2 (monotone upward)
    v3 = vm.record_session("1.2.3.4", tier_served="T1")
    assert v3["n_sessions"] == 3
    assert v3["highest_tier_served"] == "T2"

    # Fourth session: escalated to T3
    v4 = vm.record_session("1.2.3.4", tier_served="T3")
    assert v4["n_sessions"] == 4
    assert v4["highest_tier_served"] == "T3"


def test_fail_cheap_on_error(tmp_path: Path) -> None:
    # Point to a directory instead of a file to force an operational failure
    bad_path = tmp_path
    vm = VisitorMemory(bad_path, salt=b"err-salt")

    # Must fail-cheap and return fallback T1 dictionary rather than raising unhandled exception
    res = vm.get_visitor("9.9.9.9")
    assert res["highest_tier_served"] == "T1"
    assert res["n_sessions"] == 0
