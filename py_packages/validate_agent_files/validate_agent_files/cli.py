#!/usr/bin/env python3

"""CLI argument parsing for validate_agent_files."""

from __future__ import annotations

import argparse
from typing import List, Optional

from .paths import ECOSYSTEMS


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments for repository customization validation."""
    parser = argparse.ArgumentParser(description='Validate repository skills, agents, and prompts')

    parser.add_argument(
        'paths',
        nargs='*',
        default=['.'],
        help='Customization roots or files to validate (default: current directory)',
    )
    parser.add_argument(
        '--kind',
        choices=['all', 'skills', 'agents', 'prompts'],
        default='all',
        help='Customization kind to validate (default: all)',
    )
    parser.add_argument(
        '--mode',
        choices=['files', 'plugin'],
        default='files',
        help=(
            'Validation mode: "files" validates only the skills, agents, and prompts found '
            'under the given paths; "plugin" additionally validates the plugin manifests of '
            'every plugin published by a marketplace manifest, without requiring any of them '
            'to exist. Implied by --require-marketplace (default: %(default)s).'
        ),
    )
    parser.add_argument(
        '--require-marketplace',
        nargs='+',
        choices=sorted(ECOSYSTEMS),
        default=[],
        metavar='ECOSYSTEM',
        help=(
            'Require these ecosystems to publish an installable catalog: the marketplace '
            'manifest must exist, every plugin it references must be on disk, and each '
            'must carry a valid definition (choices: %(choices)s). Nothing is required '
            'by default.'
        ),
    )
    parser.add_argument(
        '--recommend',
        action='store_true',
        default=False,
        help='Show recommendations for improvement',
    )
    parser.add_argument(
        '--ci',
        action='store_true',
        default=False,
        help='Enable CI mode (no colors, structured output)',
    )
    parser.add_argument(
        '--errors-only',
        action='store_true',
        default=False,
        help='Show only errors, exclude warnings',
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json', 'csv'],
        default='text',
        help='Output format (text, json, csv)',
    )
    parser.add_argument(
        '-q', '--quiet', action='store_true', default=False, help='Suppress non-error output'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False, help='Show detailed output'
    )
    parser.add_argument(
        '--json',
        action='store_const',
        dest='format',
        const='json',
        help='Output results in JSON format (shorthand for --format json)',
    )
    parser.add_argument(
        '--csv',
        action='store_const',
        dest='format',
        const='csv',
        help='Output results in CSV format (shorthand for --format csv)',
    )

    return parser.parse_args(args)
