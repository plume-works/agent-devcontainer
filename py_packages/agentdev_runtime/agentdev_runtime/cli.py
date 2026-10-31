"""The ``agentdev-runtime`` command line: one subcommand per runtime concern."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import sys

from agentdev_runtime import settings

Handler = Callable[[argparse.Namespace], int]


def _settings_table(args: argparse.Namespace) -> int:
    print(settings.markdown_table())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='agentdev-runtime', description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True, metavar='COMMAND')
    table = commands.add_parser('settings', help='print the settings table the README carries')
    table.set_defaults(handler=_settings_table)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler: Handler = args.handler
    return handler(args)


if __name__ == '__main__':
    sys.exit(main())
