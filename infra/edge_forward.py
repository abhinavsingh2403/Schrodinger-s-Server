"""Relay two fixed lab ports, preserving TCP half-closes."""
import asyncio
from contextlib import AsyncExitStack
from functools import partial


async def copy(reader, writer):
    while chunk := await reader.read(65536):
        writer.write(chunk)
        await writer.drain()
    writer.write_eof()


async def forward(host, port, reader, writer):
    try:
        upstream, remote = await asyncio.open_connection(host, port)
        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(copy(reader, remote))
                group.create_task(copy(upstream, writer))
        finally:
            remote.close()
    finally:
        writer.close()


async def main():
    async with AsyncExitStack() as stack:
        for host, port in [('sensor', 2222), ('dashboard', 8080)]:
            await stack.enter_async_context(await asyncio.start_server(partial(forward, host, port), '0.0.0.0', port))
        await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())
