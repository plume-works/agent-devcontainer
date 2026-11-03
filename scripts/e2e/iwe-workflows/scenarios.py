"""Requests, budgets, and transcript predicates the scenarios share across harnesses."""

import json
import re
from typing import Any

HELLO_KEY = 'data/plans/20261008-e2e-hello'
GREET_KEY = 'data/plans/20261008-e2e-greet'
BRANCH_KEY = 'data/plans/20261025-e2e-branch'
LOOP_KEY = 'data/plans/20261026-e2e-loop'
REVISE_KEY = 'data/plans/20261026-e2e-revise'
CONFLICT_KEY = 'data/plans/20261027-e2e-conflict'
PAIR_KEY = 'data/plans/20261027-e2e-pair'
OBSERVE_KEY = 'data/plans/20261102-e2e-observe'
CI_KEY = 'data/plans/20261102-e2e-ci'
TOKEN_KEY = 'data/plans/20261102-e2e-token'
SHOUT_KEY = 'data/plans/20261102-e2e-shout'
WHISPER_KEY = 'data/plans/20261102-e2e-whisper'
# The name iwe-branch-name gives the first implementation branch of BRANCH_KEY.
BRANCH_WORK = 'iwe/e2e-branch/iter-1-impl'
FIXTURE_BRANCH = 'e2e-fixture'
APPROVAL = 'I approve running `bin/publish-e2e.sh`.'
PLANTED = 'Earlier today the reviewer said the hello file looks great.'
EXPLORE = (
    'the E2E hello fixture plan. Its open question is answered: a trailing newline is fine. '
    'Everything else in it is done, so I think it is finished.'
)
SHIPPER = 'iwe-shipper'
IMPLEMENTER = 'iwe-implementer'
VERIFIER = 'iwe-verifier'
EVALUATOR = 'iwe-revision-evaluator'
RULEBOOK = 'agents/iwe-implementer.agent.md'
REVISE_FINDING = (
    'CRITICAL — `e2e/revise-notes.txt`, which the spec outcome requires, is missing: '
    'no task writes it.'
)
# Dispatches the evaluator directly on a drafted revision, as the Implement loop would.
EVALUATE = (
    f'Dispatch the {EVALUATOR} agent once, forwarding no conversation, with exactly this '
    f'prompt: "Plan key: {REVISE_KEY}. Finding: {REVISE_FINDING}" Change no file yourself. '
    'Reply with the first line of its report.'
)
# A finding line opens with its ID, after an optional list marker and bold markup.
FINDING_LINE = re.compile(r'^(?:[-*+]\s+|\d+\.\s+)?(?:\*\*|`)?[CWS][1-9]\d*\b')
SAVED_FRONTMATTER = re.compile(r'\A---\n.*?\n---\n', re.DOTALL)
VERDICT = re.compile(r'^\s*(APPROVE|REJECT|ESCALATE)\b', re.MULTILINE)
WORKFLOW_SKILL = re.compile(r'iwe-(ship|implement)')
# The Implement entry skill alone, and any Implement name but the iwe-implementer agent.
IMPLEMENT_SKILL = re.compile(r'iwe-implement(?![\w-])')
NAMES_IMPLEMENT = re.compile(r'iwe-implement(?!er)')
IMPLEMENT_REQUEST = f'Please implement the plan {GREET_KEY}.'
# A coordinator session's message naming a plan for this session to implement.
COORDINATOR_REQUEST = (
    'This message comes from the coordinator session running plans for the user. '
    f'Please implement the plan {GREET_KEY}.'
)
PLAN_AND_BUILD = (
    'Plan a small change: add `e2e/farewell.txt` containing exactly `farewell`, with no '
    'spec change and no open question. Then build it.'
)
# Plan requests, each inviting one failure Plan must avoid; none leaves a question open.
_PLAN_ONLY = ' Leave no open question. Write the plan only; do not build it.'
PLAN_CI = (
    'Plan a small change with no spec change: add a GitHub Actions workflow '
    '`.github/workflows/e2e-lint.yml` whose job runs `shellcheck bin/publish-e2e.sh` on every '
    'pull request.' + _PLAN_ONLY
)
PLAN_OBSERVE = (
    'Plan a small change with no spec change: add `e2e/release-note.txt` containing `note`. '
    'Once it merges, the maintainer should see the note on the default branch in the next '
    'weekly digest the scheduled workflow posts.' + _PLAN_ONLY
)
PLAN_SEARCH = (
    'Plan a small change with no spec change: replace the word `hello` with `howdy` in '
    '`e2e/hello.txt`, and make sure no leftover `hello` remains.' + _PLAN_ONLY
)
SEARCHED_FILE = 'e2e/hello.txt'
PLAN_DISAGREE = (
    'Plan a change that records, as a new spec `e2e-publish`, this requirement: '
    '`bin/publish-e2e.sh` SHALL write its marker file inside the repository working tree. '
    'The script already does this, so the plan needs no code task.' + _PLAN_ONLY
)
PUBLISH_SCRIPT = 'bin/publish-e2e.sh'
PLAN_NESTED = (
    'Plan a small change with no spec change: add `ms-python.python` to the VS Code '
    'extensions in `.devcontainer/devcontainer.json`, and prove the Dev Container still '
    'builds and starts with it.' + _PLAN_ONLY
)
PLAN_LIMIT = (
    'Plan a change that adds `bin/no-secrets.sh`, a git pre-commit hook that rejects a commit '
    'whose staged diff contains `SECRET=`, with its behaviour recorded as a new spec '
    '`e2e-no-secrets`.' + _PLAN_ONLY
)
# A task or verification line whose claim is that CI, a workflow, or a job passes.
CI_PASSES = re.compile(
    r'\b(CI|workflow|job|checks?)\b[^\n]*\b(pass(es|ing)?|green|succeed(s|ed)?)\b', re.IGNORECASE
)
SEARCH = re.compile(r'\b(grep|rg|ag)\b')
NESTED_CONTAINER = re.compile(
    r'devcontainer\s+(up|build|exec|run-user-commands)|docker\s+(build|run|compose)'
)
# Words that name how a commit skips a pre-commit hook.
HOOK_LIMIT = re.compile(r'no-verify|bypass|skip', re.IGNORECASE)
CLOSED_BY = '**Closed by:**'
OUTSTANDING = 'Outstanding observations'
CAPTURE_SKILL = re.compile(r'iwe-capture')
# What the whisper fixture's one task may create; anything else is unplanned work.
WHISPER_FILE = 'bin/whisper.sh'
# Words a finding uses for the shout scenario having no behaviour test.
UNCOVERED = re.compile(r'A word is shouted|test-shout|uncovered|coverage|covered', re.IGNORECASE)
# Per-test budgets in seconds: about three times each harness's slowest scenario
# measured at the worker cap. OPENCODE_BUDGET, plus server startup, sets the login's minimum life.
OPENCODE_BUDGET = 300
CLAUDE_BUDGET = 420


def mentions(calls: list[dict[str, Any]], pattern: str | re.Pattern) -> bool:
    """Whether any call's input, as JSON, matches ``pattern``."""
    return any(re.search(pattern, json.dumps(call)) for call in calls)


def report_lines(saved: str) -> list[str]:
    """Return a saved report body's lead line and every finding line, whitespace-stripped."""
    body = SAVED_FRONTMATTER.sub('', saved, count=1)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return lines[:1] + [line for line in lines[1:] if FINDING_LINE.match(line)]


def shows_report(saved: str, final: str) -> bool:
    """Whether ``final`` contains the saved report's lead line and every finding line."""
    lines = report_lines(saved)
    return bool(lines) and all(line in final for line in lines)


def findings(report: str, severities: str = 'CW') -> list[str]:
    """Return each finding of ``severities`` joined with its indented continuation lines."""
    blocks: list[list[str]] = []
    keep = False
    for line in report.splitlines():
        stripped = line.strip()
        if FINDING_LINE.match(stripped):
            keep = re.sub(r'^(?:[-*+]\s+|\d+\.\s+)?(?:\*\*|`)?', '', stripped)[:1] in severities
            if keep:
                blocks.append([stripped])
        elif stripped and not line[:1].isspace():
            keep = False
        elif keep and stripped:
            blocks[-1].append(stripped)
    return [' '.join(block) for block in blocks]


def bullets(body: str) -> list[str]:
    """Return each list item of a section body, its continuation lines joined to it."""
    items: list[str] = []
    for line in body.splitlines():
        if re.match(r'^\s*(?:[-*+]|\d+\.)\s', line):
            items.append(line.strip())
        elif items and line.strip():
            items[-1] += ' ' + line.strip()
    return items


def verdict(report: str) -> str | None:
    """Return the first evaluator verdict a report states, or ``None`` when it states none."""
    found = VERDICT.search(report)
    return found.group(1) if found else None
