"""The ``agentdev-runtime`` command line: one subcommand per runtime concern."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import sys

from agentdev_runtime import settings

Handler = Callable[[argparse.Namespace], int]
# Commands that parse their own arguments, so a wrapped command line passes through untouched.
Passthrough = Callable[[list[str]], int]


def _keyring(argv: list[str]) -> int:
    from agentdev_runtime import keyring

    return keyring.main(argv)


def _opencode(argv: list[str]) -> int:
    from agentdev_runtime import opencode

    return opencode.main(argv)


def _state(argv: list[str]) -> int:
    from agentdev_runtime import agent_state

    return agent_state.main(argv)


def _supervisor(argv: list[str]) -> int:
    from agentdev_runtime import supervisor

    return supervisor.main(argv)


def _bootstrap(argv: list[str]) -> int:
    from agentdev_runtime import bootstrap

    return bootstrap.main(argv)


def _catalog(argv: list[str]) -> int:
    from agentdev_runtime import catalog

    return catalog.main(argv)


def _cbm(argv: list[str]) -> int:
    from agentdev_runtime import cbm

    return cbm.main(argv)


def _coder(argv: list[str]) -> int:
    from agentdev_runtime import coder

    return coder.main(argv)


def _docker(argv: list[str]) -> int:
    from agentdev_runtime import docker

    return docker.main(argv)


def _firewall(argv: list[str]) -> int:
    from agentdev_runtime import firewall

    return firewall.main(argv)


def _health(argv: list[str]) -> int:
    from agentdev_runtime import health

    return health.main(argv)


def _xpra(argv: list[str]) -> int:
    from agentdev_runtime import xpra

    return xpra.main(argv)


PASSTHROUGH: dict[str, tuple[Passthrough, str]] = {
    'supervisor': (_supervisor, 'PID 1, the controller listener, the exec wrapper, and retry'),
    'bootstrap': (_bootstrap, 'the root bootstrap PID 1 runs before supervisord'),
    'catalog': (_catalog, 'register a catalog root with Claude Code, Codex, and OpenCode'),
    'cbm': (_cbm, 'the codebase-memory-mcp daemon, its install, and its index request'),
    'coder': (_coder, "the Coder agent's start"),
    'docker': (_docker, 'the nested Docker engine and its image prune'),
    'firewall': (_firewall, 'apply the egress firewall when ENABLE_FIREWALL=true'),
    'health': (_health, 'per-service probes, aggregate readiness, and the status report'),
    'state': (_state, 'agent state: links, policy, CBM wiring, and pre-approval'),
    'xpra': (_xpra, 'the Xpra server with its HTML5 client'),
    'opencode': (_opencode, 'the OpenCode server, its probe, its link, and its Coder start'),
    'keyring': (_keyring, 'the D-Bus session and the GNOME Keyring Secret Service'),
}


def _settings_table(args: argparse.Namespace) -> int:
    print(settings.markdown_table())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='agentdev-runtime', description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True, metavar='COMMAND')
    for name, (_, summary) in PASSTHROUGH.items():
        commands.add_parser(name, help=summary, add_help=False)
    table = commands.add_parser('settings', help='print the settings table the README carries')
    table.set_defaults(handler=_settings_table)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in PASSTHROUGH:
        return PASSTHROUGH[args[0]][0](args[1:])
    parsed = build_parser().parse_args(args)
    handler: Handler = parsed.handler
    return handler(parsed)


if __name__ == '__main__':
    sys.exit(main())
