#!/usr/bin/env python3
"""
Forward TCP ports to another host: a stand-in for the operator's reverse proxy.

Usage: ``tcp_proxy.py <target-host> <listen-port>:<target-port> [...]``. Bytes pass through
unchanged, so HTTP and WebSocket upgrades reach the target exactly as a proxy would send them.
"""

from __future__ import annotations

import asyncio
import sys


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Copy one direction until EOF, then close the writer."""
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except ConnectionError as error:
        print(f'tcp_proxy: connection ended: {error}', file=sys.stderr)
    finally:
        writer.close()


async def serve(host: str, listen: int, target: int) -> asyncio.base_events.Server:
    async def handle(client_reader, client_writer) -> None:
        try:
            upstream_reader, upstream_writer = await asyncio.open_connection(host, target)
        except OSError as error:
            print(f'tcp_proxy: {host}:{target} unreachable: {error}', file=sys.stderr)
            client_writer.close()
            return
        await asyncio.gather(
            pipe(client_reader, upstream_writer), pipe(upstream_reader, client_writer)
        )

    return await asyncio.start_server(handle, '0.0.0.0', listen)


async def main() -> None:
    host, routes = sys.argv[1], sys.argv[2:]
    servers = []
    for route in routes:
        listen, target = (int(part) for part in route.split(':'))
        servers.append(await serve(host, listen, target))
    print('tcp_proxy: ready', flush=True)
    await asyncio.gather(*(server.serve_forever() for server in servers))


if __name__ == '__main__':
    asyncio.run(main())
