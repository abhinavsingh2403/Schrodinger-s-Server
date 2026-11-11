"""
Unit tests for gatekeeper feature extractor: parity and temporal leakage assertions.
"""

from __future__ import annotations

import pytest

from gatekeeper.feature_extractor import (
    SessionFeatureExtractor,
    extract_session_features_from_events,
)


@pytest.fixture
def sample_session_events() -> list[dict]:
    return [
        # Stage S1: Version and Kex
        {
            "eventid": "cowrie.client.version",
            "version": "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6",
        },
        {
            "eventid": "cowrie.client.kex",
            "kexAlgs": ["curve25519-sha256", "ecdh-sha2-nistp256"],
            "keyAlgs": ["rsa-sha2-512"],
            "encCS": ["chacha20-poly1305@openssh.com", "aes128-ctr"],
            "macCS": ["umac-64-etm@openssh.com"],
            "compCS": ["none"],
        },
        # Stage S2: Auth
        {
            "eventid": "cowrie.login.failed",
            "username": "root",
        },
        {
            "eventid": "cowrie.login.success",
            "username": "root",
        },
        # Stage S3: Terminal
        {
            "eventid": "cowrie.client.size",
            "width": 80,
            "height": 24,
        },
        # Stage S4: Command 1
        {
            "eventid": "cowrie.command.input",
            "input": "uname -a | grep Linux",
        },
        # Stage S5: Commands 2 & 3
        {
            "eventid": "cowrie.command.input",
            "input": "cat /etc/passwd",
        },
        {
            "eventid": "cowrie.command.input",
            "input": "ls -la",
        },
    ]


def test_offline_live_parity(sample_session_events: list[dict]) -> None:
    """AGENTS.md Rule 10: Live streaming ingestion matches offline batch extraction."""
    # Live streaming mode (event-by-event)
    live_extractor = SessionFeatureExtractor()
    for ev in sample_session_events:
        live_extractor.ingest_event(ev)
    live_s4_features = live_extractor.extract_stage_features("S4")

    # Offline batch mode
    offline_s4_features = extract_session_features_from_events(sample_session_events, "S4")

    assert live_s4_features == offline_s4_features


def test_temporal_leakage_guard(sample_session_events: list[dict]) -> None:
    """EXPERIMENT0.md Section 5: Appending future events must not alter earlier stage features."""
    early_events = sample_session_events[:4]  # S1 and S2 events only

    # S2 features before later commands arrive
    s2_early = extract_session_features_from_events(early_events, "S2")

    # S2 features after S3, S4, and S5 events have arrived
    s2_late = extract_session_features_from_events(sample_session_events, "S2")

    assert s2_early == s2_late


def test_feature_values_correctness(sample_session_events: list[dict]) -> None:
    extractor = SessionFeatureExtractor()
    for ev in sample_session_events:
        extractor.ingest_event(ev)

    s1 = extractor.extract_stage_features("S1")
    assert s1["s1_is_openssh"] == 1
    assert s1["s1_is_paramiko"] == 0
    assert s1["s1_kex_count"] == 2
    assert s1["s1_cipher_count"] == 2

    s2 = extractor.extract_stage_features("S2")
    assert s2["s2_auth_attempts"] == 2
    assert s2["s2_failed_logins"] == 1
    assert s2["s2_has_success"] == 1

    s3 = extractor.extract_stage_features("S3")
    assert s3["s3_has_pty"] == 1
    assert s3["s3_term_width"] == 80
    assert s3["s3_term_height"] == 24

    s4 = extractor.extract_stage_features("S4")
    assert s4["s4_cmd1_has_pipe"] == 1
    assert s4["s4_cmd1_has_chain"] == 0

    s5 = extractor.extract_stage_features("S5")
    assert s5["s5_cmd_count"] == 3
    assert s5["s5_unique_ratio"] == 1.0
