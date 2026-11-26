"""Relay two fixed lab ports, preserving TCP half-closes and client source identity."""
import asyncio
from contextlib import AsyncExitStack
from functools import partial
import os
import sys
from pathlib import Path

# Ensure infra package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from infra.proxy import format_proxy_v1
except ImportError:
    from proxy import format_proxy_v1  # type: ignore[no-redef]


async def copy(reader, writer):
    while chunk := await reader.read(65536):
        writer.write(chunk)
        await writer.drain()
    writer.write_eof()


async def forward(host, port, reader, writer, send_proxy_header: bool = False):
    try:
        upstream, remote = await asyncio.open_connection(host, port)
        try:
            if send_proxy_header:
                peer = writer.get_extra_info("peername")
                sock = writer.get_extra_info("sockname")
                if peer and sock:
                    proxy_line = format_proxy_v1(peer[0], sock[0], peer[1], sock[1])
                    remote.write(proxy_line)
                    await remote.drain()
            async with asyncio.TaskGroup() as group:
                group.create_task(copy(reader, remote))
                group.create_task(copy(upstream, writer))
        finally:
            remote.close()
    finally:
        writer.close()


async def main():
    async with AsyncExitStack() as stack:
        # Port 2222 forwards SSH with PROXY protocol header to preserve visitor identity across Docker ingress
        await stack.enter_async_context(
            await asyncio.start_server(partial(forward, "sensor", 2222, send_proxy_header=True), "0.0.0.0", 2222)
        )
        # Port 8080 forwards HTTP dashboard
        await stack.enter_async_context(
            await asyncio.start_server(partial(forward, "dashboard", 8080, send_proxy_header=False), "0.0.0.0", 8080)
        )
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
