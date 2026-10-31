#!/usr/bin/env python3

"""
Read a GitHub issue, with its comments, into ./.tmp for exploration.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import github_issue  # noqa: E402  (path set above so the plugin's bin/ resolves)
import result_codes as rc  # noqa: E402
from skill_common import help_header, print_error, require_git_repo, Stop  # noqa: E402

GH_UNAVAILABLE = 3
ISSUE_NOT_FOUND = 4
PREFLIGHT_ERROR = 2

DESCRIPTION = 'Read a GitHub issue, with its comments, into ./.tmp for exploration.'

USAGE = """
Usage:
  fetch-issue.py <issue>

Arguments:
  <issue>    An issue URL, OWNER/REPO#N, #N, or N. The bare forms resolve
             against the repository in the current directory.

Options:
  -h, --help    Show this help text.

Output (key=value lines):
  RESULT, ISSUE_REPO, ISSUE_NUMBER, ISSUE_URL, ISSUE_STATE, ISSUE_TITLE,
  ISSUE_FILE
  ISSUE_FILE is a Markdown file under ./.tmp holding the title, labels, body,
  and every comment, written fresh on each run.

Results (RESULT / exit code):
  SUCCESS          0  The issue was read and written to ISSUE_FILE
  ISSUE_NOT_FOUND  4  The repository has no issue with that number
  GH_UNAVAILABLE   3  gh is missing, unauthenticated, or its API call failed
  PREFLIGHT_ERROR  2  Usage or preflight error (not a repo, unparseable ref)
  SCRIPT_FAILURE   1  Unhandled error
  SIGNAL_HUP     129  Interrupted by HUP
  SIGNAL_INT     130  Interrupted by INT
  SIGNAL_TERM    143  Interrupted by TERM
"""

MARKER = '== ISSUE =='

# One gh call carries both the key lines and the document; the marker splits them.
ISSUE_TEMPLATE = """ISSUE_NUMBER={{.number}}
ISSUE_URL={{.url}}
ISSUE_STATE={{.state}}
ISSUE_TITLE={{.title}}
== ISSUE ==
# {{.title}}

- Issue: {{.url}}
- State: {{.state}}
- Author: {{.author.login}}
- Labels: {{range $i, $l := .labels}}{{if $i}}, {{end}}{{$l.name}}{{end}}

## Body

{{.body}}

## Comments
{{range .comments}}
### {{.author.login}} — {{.createdAt}}

{{.body}}
{{end}}"""


def usage() -> str:
    """Return the full help text."""
    return help_header(DESCRIPTION, __file__) + USAGE


def parse_arguments(arguments: list[str]) -> str:
    """Return the one issue reference, stopping at a usage error or help."""
    issue_ref = ''
    for argument in arguments:
        if argument in ('-h', '--help'):
            print(usage(), end='')
            raise Stop(0)
        if argument.startswith('-'):
            print_error(f'Unknown argument: {argument}')
            print(usage(), end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
        if issue_ref:
            print_error('Only one issue reference is accepted.')
            raise Stop(PREFLIGHT_ERROR)
        issue_ref = argument
    if not issue_ref:
        print_error('Missing issue reference.')
        print(usage(), end='', file=sys.stderr)
        raise Stop(PREFLIGHT_ERROR)
    return issue_ref


def run(arguments: list[str]) -> int:
    """Read the issue, print its key lines, and write the document under .tmp."""
    issue_ref = parse_arguments(arguments)
    ref = github_issue.parse_issue_ref(issue_ref)
    if ref is None:
        print_error(
            f'Unrecognized issue reference: {issue_ref} (use a URL, OWNER/REPO#N, #N, or N).'
        )
        return PREFLIGHT_ERROR
    repo_root = require_git_repo()
    if not github_issue.require_gh():
        return GH_UNAVAILABLE

    repo = ref.repo
    if not repo:
        resolved = github_issue.resolve_current_repo()
        if resolved is None:
            print_error(
                'Could not resolve the current repository; pass OWNER/REPO#N or an issue URL.'
            )
            return GH_UNAVAILABLE
        repo = resolved

    view = subprocess.run(
        [
            'gh', 'issue', 'view', ref.number, '--repo', repo,
            '--json', 'number,title,url,state,body,author,labels,comments',
            '--template', ISSUE_TEMPLATE,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )  # fmt: skip
    output = view.stdout.rstrip('\n')
    if view.returncode != 0:
        print(output, file=sys.stderr)
        if github_issue.gh_output_says_not_found(output):
            print_error(f'Issue {repo}#{ref.number} does not exist.')
            return ISSUE_NOT_FOUND
        print_error(f'gh issue view failed for {repo}#{ref.number}.')
        return GH_UNAVAILABLE

    tmp_dir = repo_root / '.tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    issue_file = tmp_dir / f'issue-{repo.replace("/", "-")}-{ref.number}.md'

    lines = output.split('\n')
    marker = lines.index(MARKER) if MARKER in lines else len(lines)
    print(f'ISSUE_REPO={repo}')
    for line in lines[:marker]:
        print(line)
    issue_file.write_text(''.join(f'{line}\n' for line in lines[marker + 1 :]))
    print(f'ISSUE_FILE={issue_file}')
    return 0


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update({GH_UNAVAILABLE: 'GH_UNAVAILABLE', ISSUE_NOT_FOUND: 'ISSUE_NOT_FOUND'})
    rc.install()
    rc.run(main)
