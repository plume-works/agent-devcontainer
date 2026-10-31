#!/usr/bin/env python3

"""
Close a GitHub issue that a filed plan now tracks, linking it in a comment.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import github_issue  # noqa: E402  (path set above so the plugin's bin/ resolves)
import result_codes as rc  # noqa: E402

COMMAND = github_issue.CloseCommand(
    description=(
        'Close a GitHub issue that a filed plan now tracks, linking the plan in a comment.'
    ),
    option='--plan',
    option_help='  --plan <path>      Repo-relative path of the plan document; it must exist.',
    comment_help='                     plan path, the current branch, and the repository.',
    missing_label='plan file',
    not_found='Plan file not found',
    comment=(
        'Planned in `{path}` on branch `{branch}` of {repo}. '
        'Closing; the plan tracks the work from here.'
    ),
)


def main() -> int:
    """Close the issue."""
    return github_issue.run_close(COMMAND, __file__, sys.argv[1:])


if __name__ == '__main__':
    rc.RESULT_CODES.update(github_issue.CLOSE_RESULTS)
    rc.install()
    rc.run(main)
