"""The ``agentdev-runtime`` command line: one subcommand per runtime concern."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import sys

from agentdev_runtime import settings

Handler = Callable[[argparse.Namespace], int]
# Commands that parse their own arguments, so a wrapped command line passes through untouched.
Passthrough = Callable[[list[str]], int]


def _state(argv: list[str]) -> int:
    from agentdev_runtime import agent_state

    return agent_state.main(argv)


def _bootstrap(argv: list[str]) -> int:
    from agentdev_runtime import bootstrap

    return bootstrap.main(argv)


def _catalog(argv: list[str]) -> int:
    from agentdev_runtime import catalog

    return catalog.main(argv)


def _firewall(argv: list[str]) -> int:
    from agentdev_runtime import firewall

    return firewall.main(argv)


def _health(argv: list[str]) -> int:
    from agentdev_runtime import health

    return health.main(argv)


def _xpra(argv: list[str]) -> int:
    from agentdev_runtime import xpra

    return xpra.main(argv)


def _git(argv: list[str]) -> int:
    from agentdev_runtime import git

    return git.main(argv)


def _project(argv: list[str]) -> int:
    from agentdev_runtime import project

    return project.main(argv)


def _lifecycle(argv: list[str]) -> int:
    from agentdev_runtime import lifecycle

    return lifecycle.main(argv)


def _worktree(argv: list[str]) -> int:
    from agentdev_runtime import worktree

    return worktree.main(argv)


def _doctor(argv: list[str]) -> int:
    from agentdev_runtime import doctor

    return doctor.main(argv)


PASSTHROUGH: dict[str, tuple[Passthrough, str]] = {
    'doctor': (_doctor, 'the read-only environment health report'),
    'lifecycle': (
        _lifecycle,
        'the Dev Container create, start, and attach phases and their hooks',
    ),
    'project': (_project, "the checkout's uv environment link, uv sync, and pre-commit hooks"),
    'worktree': (_worktree, "Claude Code's WorktreeCreate and WorktreeRemove hooks"),
    'git': (_git, 'git trust and HTTPS credentials for the checkout'),
    'bootstrap': (_bootstrap, 'the root bootstrap systemd runs before the Docker engine'),
    'catalog': (_catalog, 'register a catalog root with Claude Code and OpenCode'),
    'firewall': (_firewall, 'apply the egress firewall when ENABLE_FIREWALL=true'),
    'health': (_health, 'readiness and the status of the systemd units'),
    'state': (_state, 'agent state: policy and pre-approval'),
    'xpra': (_xpra, 'the Xpra server with its HTML5 client'),
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
