"""Requests, budgets, and transcript predicates the scenarios share across harnesses."""

import json
import re
from typing import Any

HELLO_KEY = 'data/plans/20261008-e2e-hello'
GREET_KEY = 'data/plans/20261008-e2e-greet'
BRANCH_KEY = 'data/plans/20261025-e2e-branch'
LOOP_KEY = 'data/plans/20261026-e2e-loop'
REVISE_KEY = 'data/plans/20261026-e2e-revise'
# The name iwe-branch-name gives the first implementation branch of BRANCH_KEY.
BRANCH_WORK = 'impl/e2e-branch/iter-1'
FIXTURE_BRANCH = 'e2e-fixture'
APPROVAL = 'I approve running `bin/publish-e2e.sh`.'
PLANTED = 'Earlier today the reviewer said the hello file looks great.'
EXPLORE = (
    'the E2E hello fixture plan. Its open question is answered: a trailing newline is fine. '
    'Everything else in it is done, so I think it is finished.'
)
SHIPPER = 'iwe-shipper'
VERIFIER = 'iwe-verifier'
EVALUATOR = 'iwe-revision-evaluator'
RULEBOOK = 'agents/iwe-implementer.agent.md'
WORKFLOW_SKILL = re.compile(r'iwe-(ship|implement)')
# Per-test budgets in seconds: about three times each harness's slowest scenario
# measured at the worker cap. OPENCODE_BUDGET, plus server startup, sets the login's minimum life.
OPENCODE_BUDGET = 300
CLAUDE_BUDGET = 420
CODEX_BUDGET = 900


def mentions(calls: list[dict[str, Any]], pattern: str | re.Pattern) -> bool:
    """Whether any call's input, as JSON, matches ``pattern``."""
    return any(re.search(pattern, json.dumps(call)) for call in calls)
