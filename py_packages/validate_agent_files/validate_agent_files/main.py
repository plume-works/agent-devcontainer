#!/usr/bin/env python3

"""Main orchestration function for validate_agent_files."""

from __future__ import annotations

import sys
from typing import List, Optional

from .cli import parse_arguments
from .core import CustomizationsValidationEngine
from .formatters import format_results


def main(args: Optional[List[str]] = None) -> int:
    """Run the validate_agent_files tool."""
    parsed_args = parse_arguments(args)

    # --errors-only wins over --recommend. Both destinations are always
    # defined by the parser, so read them directly: a getattr default would
    # mask a rename instead of raising.
    show_warnings = parsed_args.recommend and not parsed_args.errors_only

    engine = CustomizationsValidationEngine(
        show_warnings=show_warnings,
        require_marketplaces=getattr(parsed_args, 'require_marketplace', []),
        mode=getattr(parsed_args, 'mode', 'files'),
    )
    results = engine.validate_paths(parsed_args.paths, parsed_args.kind)

    # Compute exit code before formatting so it can be reused for CI behavior.
    exit_code = 1 if any(not result.is_valid for result in results) else 0

    formatted = format_results(results, output_format=parsed_args.format)

    # Control output based on verbosity / CI / quiet flags. Use getattr with
    # defaults so this remains robust even if some flags are not defined.
    is_quiet = getattr(parsed_args, 'quiet', False)
    is_ci = getattr(parsed_args, 'ci', False)
    is_verbose = getattr(parsed_args, 'verbose', False)

    if not is_quiet and formatted:
        if not is_ci:
            # Default behavior (non-CI): always print formatted results.
            print(formatted)
        else:
            # CI mode: only print on failure, or when explicitly verbose.
            if exit_code != 0 or is_verbose:
                print(formatted)

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
