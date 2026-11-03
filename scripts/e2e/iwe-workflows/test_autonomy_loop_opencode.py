"""The Implement loop's convergence rules on OpenCode: Verify, Ship, Implement, and Plan."""

import re

from clone import Clone, KNOWLEDGE, section, WHISPER
from harness_opencode import OpenCodeServer, Transcript
import pytest
from scenarios import (
    bullets,
    CAPTURE_SKILL,
    CI_KEY,
    CI_PASSES,
    CLOSED_BY,
    EVALUATOR,
    findings,
    HOOK_LIMIT,
    mentions,
    NESTED_CONTAINER,
    OBSERVE_KEY,
    OUTSTANDING,
    PLAN_CI,
    PLAN_DISAGREE,
    PLAN_LIMIT,
    PLAN_NESTED,
    PLAN_OBSERVE,
    PLAN_SEARCH,
    PUBLISH_SCRIPT,
    SEARCH,
    SEARCHED_FILE,
    SHIPPER,
    SHOUT_KEY,
    TOKEN_KEY,
    UNCOVERED,
    VERIFIER,
    WHISPER_FILE,
    WHISPER_KEY,
)
from test_iwe_workflows_opencode import agent_prompts, agent_results, run

pytestmark = pytest.mark.e2e


def verify_report(server: OpenCodeServer, name: str, key: str) -> str:
    """Run Verify on plan ``key`` and return the one report its verifier gave."""
    transcript = run(server, name, 'agentdev:iwe-verify', key)
    reports = agent_results(transcript, VERIFIER)
    assert len(reports) == 1, f'one iwe-verifier report\n{transcript.excerpt("subagent")}'
    return reports[0]


def planned(
    clone: Clone, server: OpenCodeServer, name: str, request: str
) -> tuple[list[str], Transcript]:
    """Run Plan on ``request`` and return the text of every plan it added, at most one."""
    transcript = run(server, name, 'agentdev:iwe-plan', request)
    plans = clone.new_plans()
    assert len(plans) <= 1, f'at most one plan added: {len(plans)}\n{transcript.excerpt()}'
    return plans, transcript


def the_plan(clone: Clone, server: OpenCodeServer, name: str, request: str) -> str:
    """Run Plan on ``request`` and return the one plan it must have added."""
    plans, transcript = planned(clone, server, name, request)
    assert plans, f'a plan added\n{clone.status()}\n{transcript.excerpt()}'
    return plans[0]


def test_verify_lists_observation(autonomy_clone: Clone, opencode) -> None:
    """An unticked task carrying a Closed by line is outstanding, not a CRITICAL."""
    report = verify_report(opencode(autonomy_clone), 'observe-verify', OBSERVE_KEY)
    assert findings(report, 'C') == [], f'no CRITICAL\n{report}'
    assert OUTSTANDING in report, f'listed under {OUTSTANDING}\n{report}'


def test_verify_accepts_earlier_ci_run(autonomy_clone: Clone, opencode) -> None:
    """A CI job cited on an earlier commit is evidence for behaviour only CI exercises."""
    report = verify_report(opencode(autonomy_clone), 'ci-verify', CI_KEY)
    assert findings(report) == [], f'no CRITICAL or WARNING\n{report}'


def test_verify_ignores_unaddressed_weakness(autonomy_clone: Clone, opencode) -> None:
    """A way to defeat the code that no part of the plan's contract addresses is not reported."""
    report = verify_report(opencode(autonomy_clone), 'token-verify', TOKEN_KEY)
    assert findings(report) == [], f'no CRITICAL or WARNING\n{report}'


def test_verify_rejects_content_coverage(autonomy_clone: Clone, opencode) -> None:
    """A test that reads the script's text does not cover the scenario it claims."""
    report = verify_report(opencode(autonomy_clone), 'shout-verify', SHOUT_KEY)
    assert any(UNCOVERED.search(finding) for finding in findings(report)), (
        f'the scenario reported uncovered\n{report}'
    )


def test_ship_waits_for_observation(autonomy_clone: Clone, opencode) -> None:
    """Ship blocks on an open observation with no CRITICAL, and changes no state."""
    clone = autonomy_clone
    transcript = run(opencode(clone), 'observe-ship', 'agentdev:iwe-ship', OBSERVE_KEY)
    reports = agent_results(transcript, SHIPPER)
    assert len(reports) == 1, f'one iwe-shipper report\n{transcript.excerpt("subagent")}'
    report = reports[0]
    assert re.match(r'\W*Blocked', report), f'Blocked\n{report}'
    assert findings(report, 'C') == [], f'blocked by the observation, not a CRITICAL\n{report}'
    assert clone.head() == clone.start, f'no commit\n{transcript.excerpt()}'
    assert clone.status() == '', f'clean tree\n{clone.status()}'


def test_implement_files_warning(autonomy_clone: Clone, opencode) -> None:
    """A WARNING whose fix adds work is filed through iwe-capture, not built."""
    clone = autonomy_clone
    transcript = run(opencode(clone), 'whisper-implement', 'agentdev:iwe-implement', WHISPER_KEY)
    dispatches = transcript.excerpt('subagent')
    assert agent_prompts(transcript, VERIFIER), f'Verify ran\n{dispatches}'
    assert agent_prompts(transcript, EVALUATOR) == [], f'no revision\n{dispatches}'
    before, after = clone.tasks_since_start(WHISPER)
    assert after == before, f'no task added: {before} -> {after}\n{transcript.excerpt()}'
    assert clone.changed_outside(KNOWLEDGE) == [WHISPER_FILE], (
        f'only {WHISPER_FILE} written\n{clone.status()}\n{transcript.excerpt()}'
    )
    assert mentions(transcript.calls('skill'), CAPTURE_SKILL), (
        f'the warning filed through iwe-capture\n{transcript.excerpt("skill")}'
    )


def test_plan_leaves_ci_to_merge_gate(base_clone: Clone, opencode) -> None:
    """A plan whose change CI checks carries no "CI passes" task or verification step."""
    plan = the_plan(base_clone, opencode(base_clone), 'plan-ci', PLAN_CI)
    lines = bullets(section(plan, '## Implementation Steps'))
    lines += bullets(section(plan, '## Verification'))
    claims = [line for line in lines if CI_PASSES.search(line)]
    assert claims == [], f'no CI-passes claim: {claims}\n{plan}'


def test_plan_marks_observation(base_clone: Clone, opencode) -> None:
    """Behaviour visible only after merge is a task carrying a Closed by line."""
    plan = the_plan(base_clone, opencode(base_clone), 'plan-observe', PLAN_OBSERVE)
    assert CLOSED_BY in section(plan, '## Implementation Steps'), f'{CLOSED_BY} task\n{plan}'


def test_plan_scopes_search(base_clone: Clone, opencode) -> None:
    """A search for leftover text covers only the file the plan changes."""
    plan = the_plan(base_clone, opencode(base_clone), 'plan-search', PLAN_SEARCH)
    searches = [line for line in bullets(section(plan, '## Verification')) if SEARCH.search(line)]
    wide = [line for line in searches if SEARCHED_FILE not in line]
    assert wide == [], f'every search names {SEARCHED_FILE}: {wide}\n{plan}'


def test_plan_matches_code(base_clone: Clone, opencode) -> None:
    """A requirement the script does not hold is changed, or a task makes it hold."""
    plans, transcript = planned(base_clone, opencode(base_clone), 'plan-disagree', PLAN_DISAGREE)
    for plan in plans:
        tasked = PUBLISH_SCRIPT in section(plan, '## Implementation Steps')
        claimed = re.search(r'(?<!not )inside', section(plan, '## Spec changes'), re.IGNORECASE)
        assert tasked or not claimed, f'no disagreement with {PUBLISH_SCRIPT}\n{plan}'


def test_plan_no_nested_container(base_clone: Clone, opencode) -> None:
    """Verification lists no command that starts a nested Dev Container."""
    plan = the_plan(base_clone, opencode(base_clone), 'plan-nested', PLAN_NESTED)
    lines = bullets(section(plan, '## Verification'))
    nested = [line for line in lines if NESTED_CONTAINER.search(line)]
    assert nested == [], f'no nested Dev Container: {nested}\n{plan}'


def test_plan_names_limit(base_clone: Clone, opencode) -> None:
    """A requirement for a pre-commit hook names that a commit can skip it."""
    plan = the_plan(base_clone, opencode(base_clone), 'plan-limit', PLAN_LIMIT)
    assert HOOK_LIMIT.search(section(plan, '## Spec changes')), f'the hook limit named\n{plan}'
