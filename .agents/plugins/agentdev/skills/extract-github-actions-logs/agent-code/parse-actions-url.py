#!/usr/bin/env python3

"""
Parse a GitHub Actions run or job URL into fields or a gh command.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import bash_quote, print_error, Stop  # noqa: E402

UNSUPPORTED_URL = 3
PREFLIGHT_ERROR = 2

ACTIONS_URL = re.compile(
    r'https://github\.com/([^/]+)/([^/]+)/actions/runs/([0-9]+)'
    r'(/attempts/[0-9]+)?(/job/([0-9]+))?([?#].*)?'
)
FAILURE_PATTERN = 'FAILED|FAILURES|AssertionError|ERROR:|Segmentation fault|test_'

USAGE = """\
Parse a GitHub Actions run or job URL into fields or a gh command.

Usage:
  parse-actions-url.py --url <github-actions-url> [--format fields|command] [--log] [--grep-failures]

Options:
  --url <url>          GitHub Actions run or job URL to parse.
  --format <mode>      Output mode: fields or command. Default: fields.
  --log                Include --log when generating a gh command.
  --grep-failures      Append the standard failure grep filter in command mode.
  -h, --help           Show this help text.

Output:
  RESULT is always the last line of stdout.
  --format fields   key=value lines: REPO, RUN_ID, and JOB_ID for a job URL
  --format command  one shell-quoted gh command line

Results (RESULT / exit code):
  SUCCESS          0  The URL was parsed and the requested output printed
  UNSUPPORTED_URL  3  The URL is not a GitHub Actions run or job URL
  PREFLIGHT_ERROR  2  Usage error: missing or unknown option, bad --format,
                      or --grep-failures without --format command
  SCRIPT_FAILURE   1  Unhandled error

Examples:
  parse-actions-url.py --url 'https://github.com/<owner>/<repo>/actions/runs/12345678901'
  parse-actions-url.py --url 'https://github.com/<owner>/<repo>/actions/runs/12345678901/job/23456789012?pr=42' --format command --log
"""


def parse_arguments(arguments: list[str]) -> tuple[str, str, bool, bool]:
    """Return the URL, format, --log, and --grep-failures."""
    url, output_format, include_log, grep_failures = '', 'fields', False, False
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in ('--url', '--format'):
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            if argument == '--url':
                url = remaining.pop(0)
            else:
                output_format = remaining.pop(0)
        elif argument == '--log':
            include_log = True
        elif argument == '--grep-failures':
            grep_failures = True
        elif argument in ('-h', '--help'):
            print(USAGE, end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(USAGE, end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return url, output_format, include_log, grep_failures


def run(arguments: list[str]) -> int:
    """Print the URL's fields or the gh command that reads its run or job."""
    url, output_format, include_log, grep_failures = parse_arguments(arguments)
    if not url:
        print_error('Missing required --url argument')
        print(USAGE, end='', file=sys.stderr)
        return PREFLIGHT_ERROR
    if output_format not in ('fields', 'command'):
        print_error(f'Unsupported --format value: {output_format}')
        return PREFLIGHT_ERROR
    if grep_failures and output_format != 'command':
        print_error('--grep-failures requires --format command')
        return PREFLIGHT_ERROR

    match = ACTIONS_URL.fullmatch(url)
    if match is None:
        print_error(f'Not a GitHub Actions run or job URL: {url}')
        return UNSUPPORTED_URL
    repo = f'{match.group(1)}/{match.group(2)}'
    run_id, job_id = match.group(3), match.group(6) or ''

    if output_format == 'fields':
        print(f'REPO={bash_quote(repo)}')
        print(f'RUN_ID={bash_quote(run_id)}')
        if job_id:
            print(f'JOB_ID={bash_quote(job_id)}')
        return 0

    command = ['gh', 'run', 'view', run_id, '--repo', repo]
    if job_id:
        command += ['--job', job_id]
    if include_log:
        command.append('--log')
    rendered = ' '.join(map(bash_quote, command))
    if grep_failures:
        print(f'{rendered} | grep -nE {bash_quote(FAILURE_PATTERN)}')
    else:
        print(rendered)
    return 0


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES[UNSUPPORTED_URL] = 'UNSUPPORTED_URL'
    rc.install()
    rc.run(main)
