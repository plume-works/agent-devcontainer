#!/usr/bin/env python3
"""
Relay TCP connections from a listen address to the session's agent proxy.

Usage: agent-proxy-relay.py LISTEN_HOST LISTEN_PORT TARGET_HOST TARGET_PORT
Design: architecture/cloud-session-host-toolchain.
"""

import asyncio
import sys

CHUNK = 65536


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Copy bytes from reader to writer until EOF, then close the writer."""
    try:
        while chunk := await reader.read(CHUNK):
            writer.write(chunk)
            await writer.drain()
    except ConnectionError as error:
        print(f'agent-proxy-relay: {error}', file=sys.stderr)
    finally:
        writer.close()


async def serve(listen_host: str, listen_port: int, target_host: str, target_port: int) -> None:
    """Accept connections forever, splicing each one to the target."""

    async def handle(client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter) -> None:
        try:
            target_r, target_w = await asyncio.open_connection(target_host, target_port)
        except OSError as error:
            print(f'agent-proxy-relay: target unreachable: {error}', file=sys.stderr)
            client_w.close()
            return
        await asyncio.gather(pipe(client_r, target_w), pipe(target_r, client_w))

    server = await asyncio.start_server(handle, listen_host, listen_port)
    async with server:
        await server.serve_forever()


def main(argv: list[str]) -> int:
    """Parse the four positional arguments and run the relay."""
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    listen_host, listen_port, target_host, target_port = argv
    try:
        asyncio.run(serve(listen_host, int(listen_port), target_host, int(target_port)))
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
