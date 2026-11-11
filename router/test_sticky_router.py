"""
Tests for Sticky Multi-Instance TCP Router (router/sticky_router.py).
Pre-registered in SPEC.md Section 5.3 and DECISIONS.md.
Uses standard library asyncio.run() to avoid external pytest plugins.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import pytest
from gatekeeper.visitor_memory import VisitorMemory
from router.sticky_router import StickyRouter, TierBackendConfig


def test_sticky_router_tier_selection_default_t1():
    """Verify that a new unknown visitor routes to T1."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        memory = VisitorMemory(db_path=os.path.join(tmp_dir, "test_router_mem.db"))
        router = StickyRouter(
            visitor_memory=memory,
            backends=TierBackendConfig(t1_port=9001, t2_port=9002, t3_port=9003),
        )

        tier, port = router.select_backend("198.51.100.55")
        assert tier == "T1"
        assert port == 9001


def test_sticky_router_tier_selection_escalated_visitor():
    """Verify that a returning visitor with T2 history routes stickily to T2."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        memory = VisitorMemory(db_path=os.path.join(tmp_dir, "test_router_mem.db"))
        # Pre-record visitor with highest_tier_served = T2
        memory.record_session("198.51.100.66", tier_served="T2")

        router = StickyRouter(
            visitor_memory=memory,
            backends=TierBackendConfig(t1_port=9001, t2_port=9002, t3_port=9003),
        )

        tier, port = router.select_backend("198.51.100.66")
        assert tier == "T2"
        assert port == 9002


def test_sticky_router_fail_cheap_on_error():
    """Verify that database failure safely falls back to T1 without crashing."""
    class BrokenMemory:
        def get_visitor(self, ip: str):
            raise RuntimeError("Database connection crashed")

    router = StickyRouter(
        visitor_memory=BrokenMemory(),
        backends=TierBackendConfig(t1_port=9001, t2_port=9002, t3_port=9003),
    )

    tier, port = router.select_backend("198.51.100.77")
    assert tier == "T1"
    assert port == 9001


def test_sticky_router_tcp_splicing_loopback():
    """Verify actual TCP stream splicing between client and mock backend."""
    async def _async_test():
        backend_received = []

        async def mock_t1_server(reader, writer):
            data = await reader.read(1024)
            backend_received.append(data)
            writer.write(b"SSH-2.0-CowrieMock\r\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(mock_t1_server, "127.0.0.1", 0)
        backend_port = server.sockets[0].getsockname()[1]

        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = VisitorMemory(db_path=os.path.join(tmp_dir, "test_splicing.db"))
            router = StickyRouter(
                visitor_memory=memory,
                backends=TierBackendConfig(t1_port=backend_port, t2_port=9992, t3_port=9993),
                listen_host="127.0.0.1",
                listen_port=0,
            )

            router_srv = await router.start()
            router_port = router_srv.sockets[0].getsockname()[1]

            # Client connects through router
            c_reader, c_writer = await asyncio.open_connection("127.0.0.1", router_port)
            c_writer.write(b"CLIENT_HELLO\n")
            await c_writer.drain()

            resp = await c_reader.read(1024)
            assert resp == b"SSH-2.0-CowrieMock\r\n"
            assert backend_received == [b"CLIENT_HELLO\n"]

            c_writer.close()
            await c_writer.wait_closed()

            await router.stop()
            server.close()
            await server.wait_closed()

    asyncio.run(_async_test())
