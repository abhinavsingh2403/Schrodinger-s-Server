"""Tests for S3 Spike Part 2: Event-level Day Sample and Schema Verification."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import pytest

from analysis.s3_event_sample import (
    REQUIRED_EVENT_FIELDS,
    verify_event_schema,
)


def test_verify_event_schema_all_present():
    """Verify that when all required fields are present, status is VERIFIED."""
    mock_events = [
        {
            "ts": "2025-06-27T00:00:01.000000Z",
            "eventid": "cowrie.session.connect",
            "session": "s_123",
            "sensor": "node_01",
            "group": 1,
            "hassh": "b1b72...",
            "version": "SSH-2.0-OpenSSH_8.9",
            "width": 80,
            "height": 24,
            "input": "uname -a",
            "src_ip": "192.0.2.1",
        }
    ]

    report = verify_event_schema(mock_events)
    assert report["status"] == "VERIFIED"
    assert report["sample_events_count"] == 1
    assert len(report["required_fields_missing"]) == 0
    assert set(report["required_fields_present"]) == set(REQUIRED_EVENT_FIELDS)


def test_verify_event_schema_partial():
    """Verify that when required fields are missing, status is PARTIAL."""
    mock_events = [
        {
            "ts": "2025-06-27T00:00:01.000000Z",
            "session": "s_123",
            # missing group, hassh, version, etc.
        }
    ]

    report = verify_event_schema(mock_events)
    assert report["status"] == "PARTIAL"
    assert "group" in report["required_fields_missing"]
    assert "hassh" in report["required_fields_missing"]
    assert "session" in report["required_fields_present"]
