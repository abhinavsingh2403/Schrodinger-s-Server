"""
Sticky Multi-Instance TCP Router.
Pre-registered in SPEC.md Section 5.3 (Plan B fallback) and DECISIONS.md.

Accepts TCP connections, queries visitor memory for the visitor's highest tier,
and splices the connection to the appropriate internal backend (T1, T2, or T3).
Guarantees:
1. Pure stream splicing: byte-for-byte fidelity without modifying the SSH stream.
2. Invariant: Monotone upward-only, sticky routing across sessions.
3. Fail-cheap: Defaults to T1 backend if visitor memory is unreachable.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional, Tuple

logger = logging.getLogger("router.sticky")


@dataclass
class TierBackendConfig:
    """Internal host and port configuration for backend honeypot tiers."""
    t1_host: str = "127.0.0.1"
    t1_port: int = 2221
    t2_host: str = "127.0.0.1"
    t2_port: int = 2222
    t3_host: str = "127.0.0.1"
    t3_port: int = 2223


class StickyRouter:
    """Asyncio TCP router with sticky session affinity to assigned honeypot tiers."""

    def __init__(
        self,
        visitor_memory: Any,
        backends: Optional[TierBackendConfig] = None,
        listen_host: str = "0.0.0.0",
        listen_port: int = 2220,
    ) -> None:
        self.visitor_memory = visitor_memory
        self.backends = backends or TierBackendConfig()
        self.listen_host = listen_host
        self.listen_port = listen_port
        self._server: Optional[asyncio.Server] = None

    def select_backend(self, client_ip: str) -> Tuple[str, int]:
        """
        Determines the destination tier and port for a client IP.
        Enforces sticky upward-only routing and fail-cheap defaults to T1.
        """
        try:
            visitor = self.visitor_memory.get_visitor(client_ip)
            tier = visitor.get("highest_tier_served", "T1").upper()
            if tier == "T3":
                return "T3", self.backends.t3_port
            elif tier == "T2":
                return "T2", self.backends.t2_port
            return "T1", self.backends.t1_port
        except Exception as exc:
            logger.warning("Router lookup failed for %s (%s); defaulting to T1", client_ip, exc)
            return "T1", self.backends.t1_port

    async def _pipe(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Bi-directional raw byte stream pipe."""
        try:
            while not reader.at_eof():
                data = await reader.read(8192)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_connection(
        self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming TCP connection and splice to backend."""
        peer = client_writer.get_extra_info("peername")
        client_ip = peer[0] if peer else "127.0.0.1"

        tier, backend_port = self.select_backend(client_ip)
        backend_host = (
            self.backends.t3_host if tier == "T3"
            else self.backends.t2_host if tier == "T2"
            else self.backends.t1_host
        )

        logger.info("Routing client %s to %s backend on port %d", client_ip, tier, backend_port)

        try:
            b_reader, b_writer = await asyncio.open_connection(backend_host, backend_port)
        except Exception as exc:
            logger.error("Failed to connect to %s backend (%s:%d): %s", tier, backend_host, backend_port, exc)
            client_writer.close()
            await client_writer.wait_closed()
            return

        # Splice client and backend streams concurrently
        pipe_forward = asyncio.create_task(self._pipe(client_reader, b_writer))
        pipe_backward = asyncio.create_task(self._pipe(b_reader, client_writer))

        await asyncio.gather(pipe_forward, pipe_backward, return_exceptions=True)

    async def start(self) -> asyncio.Server:
        """Start listening for connections."""
        self._server = await asyncio.start_server(
            self._handle_connection, self.listen_host, self.listen_port
        )
        return self._server

    async def stop(self) -> None:
        """Gracefully close the listening server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
