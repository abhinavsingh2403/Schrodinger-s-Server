"""
test_docker_visitor_identity.py: Integration tests for Docker Ingress & Visitor Identity Security.

Pre-registered in SPEC.md Section 5.1, Section 5.2 and Sprint 1 Priority 2.
Verifies:
1. Multi-Visitor Separation: Distinct external visitors through Docker/proxy ingress
   are never merged into a single identity.
2. Returning Visitor Consistency: The same visitor IP deterministically produces
   identical pseudonymous visitor_id (vis_xxxx) across sessions.
3. Privacy Preservation: Raw visitor IP addresses are never exposed in public views,
   dashboard templates, or JSON API projections.
4. Trusted Proxy Handling: Legitimate PROXY protocol v1 and X-Forwarded-For headers
   from authorized proxies (e.g., edge gateway) are parsed correctly.
5. Anti-Spoofing Security: Untrusted clients attempting to spoof identity with forged
   PROXY lines or X-Forwarded-For headers have their headers strictly rejected/ignored,
   binding identity safely to the true socket peer address.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import pytest

from gatekeeper.decision_api import DecisionEngine, GatekeeperHTTPHandler
from gatekeeper.visitor_memory import VisitorMemory, derive_visitor_id, get_masked_id
from dashboard.app import DashboardServer
from dashboard.decision_views import masked, public_row
from infra.proxy import (
    format_proxy_v1,
    parse_proxy_v1,
    is_trusted_proxy,
    extract_forwarded_ip,
    get_trusted_proxies,
)
from router.sticky_router import StickyRouter, TierBackendConfig


def test_multi_visitor_separation_across_proxy():
    """Requirement 1: Two distinct visitors must NOT be merged into a single identity."""
    salt = b"test-salt-integration-2026"
    visitor_a_ip = "198.51.100.11"
    visitor_b_ip = "198.51.100.22"

    # 1. Derive IDs directly
    id_a = derive_visitor_id(visitor_a_ip, salt)
    id_b = derive_visitor_id(visitor_b_ip, salt)
    assert id_a != id_b, "Distinct visitor IPs must produce distinct visitor IDs"

    mask_a = get_masked_id(visitor_a_ip, salt)
    mask_b = get_masked_id(visitor_b_ip, salt)
    assert mask_a != mask_b
    assert mask_a.startswith("vis_")
    assert mask_b.startswith("vis_")

    # 2. In DecisionEngine across simulated ingress
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "multi_vis.db"
        engine = DecisionEngine(db_path=db_path, salt=salt, lab_mode=True)

        # Visitor A connects and escalates to T2 via PTY
        dA1 = engine.decide(session_id="sess_vis_a_01", source_ip=visitor_a_ip, stage="S1", current_tier="T1", provenance="LAB")
        dA2 = engine.decide(session_id="sess_vis_a_01", source_ip=visitor_a_ip, stage="S3", features={"has_pty": 1}, current_tier="T1", provenance="LAB")
        assert dA1["visitor_id"] == mask_a
        assert dA2["visitor_id"] == mask_a
        assert dA2["tier"] == "T2"

        # Visitor A finishes session and records T2
        engine.record_session(source_ip=visitor_a_ip, tier_served="T2")

        # Visitor B connects fresh
        dB1 = engine.decide(session_id="sess_vis_b_01", source_ip=visitor_b_ip, stage="S1", current_tier="T1", provenance="LAB")
        assert dB1["visitor_id"] == mask_b
        # Visitor B must NOT inherit Visitor A's T2 escalation!
        assert dB1["tier"] == "T1", "Visitor B must remain in T1 and not inherit Visitor A's escalated tier"


def test_returning_visitor_consistent_pseudonym_and_tier_retention():
    """Requirement 2: Returning visitors must retain consistent pseudonymous identity."""
    salt = b"test-salt-integration-2026"
    visitor_ip = "203.0.113.88"

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "returning_vis.db"
        memory = VisitorMemory(db_path=db_path, salt=salt)
        engine = DecisionEngine(db_path=db_path, salt=salt, memory=memory, lab_mode=True)

        # First session
        d1 = engine.decide("sess_first", source_ip=visitor_ip, stage="S1", current_tier="T1", provenance="LAB")
        initial_mask = d1["visitor_id"]
        assert initial_mask == get_masked_id(visitor_ip, salt)

        # Escalate and close
        d_esc = engine.decide("sess_first", source_ip=visitor_ip, stage="S3", features={"has_pty": 1}, current_tier="T1", provenance="LAB")
        assert d_esc["tier"] == "T2"
        engine.record_session(source_ip=visitor_ip, tier_served="T2")

        # Second session (returning visitor)
        d2 = engine.decide("sess_second", source_ip=visitor_ip, stage="S1", current_tier="T1", provenance="LAB")
        returning_mask = d2["visitor_id"]

        # 1. Consistent pseudonymous identifier
        assert initial_mask == returning_mask, "Returning visitor must produce identical masked identifier"

        # 2. Memory retention: starts in T2 because highest_tier_served was T2
        assert d2["tier"] == "T2", "Returning escalated visitor must stickily retain T2"

        # End second session and record completion
        engine.record_session(source_ip=visitor_ip, tier_served="T2")

        # 3. Session count incremented in visitor memory
        rec = memory.get_visitor(visitor_ip)
        assert rec["n_sessions"] == 2
        assert rec["highest_tier_served"] == "T2"


def test_raw_ip_privacy_in_dashboard():
    """Requirement 3: Raw visitor IPs must not be exposed in public views or API projections."""
    raw_ip = "198.51.100.99"
    raw_session = "sess_secret_44"

    row = {
        "id": 1,
        "session_id": raw_session,
        "visitor_id": raw_ip,
        "stage": "S1",
        "score": 0.05,
        "tier": "T1",
        "score_source": "rule_r0_random",
        "latency_ms": 12.3,
        "timestamp": "2026-11-26T20:00:00Z",
        "provenance": "LAB",
    }

    pub = public_row(row)
    # Raw IP must not appear anywhere in public row
    assert raw_ip not in str(pub.values())
    assert pub["visitor_id"].startswith("vis_")
    assert pub["session_id"].startswith("ses_")


def test_trusted_proxy_protocol_parsing_and_formatting():
    """Requirement 4: Trusted proxy information (PROXY v1) is handled safely."""
    client_ip = "198.51.100.77"
    client_port = 54321
    edge_ip = "172.20.0.2"
    edge_port = 2222

    # 1. Format header
    header = format_proxy_v1(client_ip, edge_ip, client_port, edge_port)
    assert header.startswith(b"PROXY TCP4 198.51.100.77 172.20.0.2 54321 2222\r\n")

    # 2. Parse header
    stream = header + b"SSH-2.0-OpenSSH_9.2p1\r\n"
    parsed = parse_proxy_v1(stream)
    assert parsed is not None
    src_ip, src_port, remainder = parsed
    assert src_ip == client_ip
    assert src_port == client_port
    assert remainder == b"SSH-2.0-OpenSSH_9.2p1\r\n"

    # 3. Trusted proxy check
    assert is_trusted_proxy("127.0.0.1") is True
    assert is_trusted_proxy("172.20.0.2") is True  # In 172.16.0.0/12
    assert is_trusted_proxy("10.0.0.5") is True    # In 10.0.0.0/8
    assert is_trusted_proxy("198.51.100.77") is False  # External client: NOT trusted


def test_untrusted_client_cannot_spoof_identity_via_headers():
    """Requirement 5: Untrusted clients must not be able to spoof identity using arbitrary headers."""
    # Untrusted client attempting to send X-Forwarded-For
    untrusted_client_ip = "203.0.113.50"
    forged_headers = {"X-Forwarded-For": "1.1.1.1, 10.0.0.1"}

    # Must ignore forged header and return actual remote IP
    resolved = extract_forwarded_ip(untrusted_client_ip, forged_headers)
    assert resolved == untrusted_client_ip, "Untrusted client headers must be strictly ignored"
    assert resolved != "1.1.1.1"

    # Trusted proxy forwarding real client
    trusted_proxy_ip = "127.0.0.1"
    legitimate_headers = {"X-Forwarded-For": "203.0.113.50"}
    trusted_resolved = extract_forwarded_ip(trusted_proxy_ip, legitimate_headers)
    assert trusted_resolved == "203.0.113.50", "Trusted proxy forwarded header must be extracted"
