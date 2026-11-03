"""
OpenCode scenarios for the failures the converging Implement loop removes.

Plan: data/plans/20261102-autonomy-loop. Each scenario fails until that plan's
rulebook changes land.
"""

from collections.abc import Callable
from pathlib import Path
import re

from autonomy import (
    add_ci,
    add_cover,
    add_observe,
    add_weak,
    CI_KEY,
    ci_pass_steps,
    claims_inside_only,
    COVER_KEY,
    findings,
    lead,
    names_limit,
    new_plans,
    OBSERVATION,
    OBSERVE_KEY,
    PLAN_CI,
    PLAN_CONTRADICT,
    PLAN_DEVCONTAINER,
    PLAN_LIMIT,
    PLAN_OBSERVE,
    PLAN_RENAME,
    planned_files,
    PLANS,
    SCENARIO,
    section,
    stub_warning_verifier,
    UNATTENDED,
    unscoped_searches,
    WARNED_WORK,
    WEAK_KEY,
)
from clone import Clone, LOOP, TASK_HEADING
from harness_opencode import OpenCodeServer, Transcript
import pytest
from scenarios import (
    EVALUATOR,
    LOOP_KEY,
    mentions,
    OPENCODE_BUDGET,
    PLAN_BUDGET,
    SHIPPER,
    VERIFIER,
)
from test_iwe_workflows_opencode import agent_prompts, agent_results

pytestmark = pytest.mark.e2e
Start = Callable[[Clone], OpenCodeServer]


def run(
    server: OpenCodeServer, name: str, command: str, text: str, budget: float = OPENCODE_BUDGET
) -> Transcript:
    """Run one command and assert, first, that the run completed on a working login."""
    transcript = server.run(name, command, text, budget)
    reason = transcript.failure_reason(budget)
    assert reason is None, f'opencode run did not complete: {reason}\n{transcript.excerpt()}'
    return transcript


def verify_report(clone: Clone, opencode: Start, name: str, key: str) -> str:
    """Run Verify on ``key`` and return the one verifier report."""
    transcript = run(opencode(clone), name, 'agentdev:iwe-verify', key)
    reports = agent_results(transcript, VERIFIER)
    assert len(reports) == 1, f'one iwe-verifier report\n{transcript.excerpt("subagent")}'
    return reports[0]


def plan_run(
    clone: Clone, opencode: Start, name: str, request: str
) -> tuple[Transcript, list[Path]]:
    """Run Plan on ``request`` and return the run with every plan file it added."""
    text = f'{request}{UNATTENDED}'
    transcript = run(opencode(clone), name, 'agentdev:iwe-plan', text, PLAN_BUDGET)
    return transcript, new_plans(clone)


def written_plan(clone: Clone, opencode: Start, name: str, request: str) -> str:
    """Run Plan on ``request`` and return the one plan it wrote."""
    transcript, plans = plan_run(clone, opencode, name, request)
    assert len(plans) == 1, f'one plan written: {plans}\n{transcript.excerpt()}'
    return plans[0].read_text()


def test_verify_lists_observation(base_clone: Clone, opencode: Start) -> None:
    """An unticked post-merge observation is listed as outstanding, not as a CRITICAL."""
    add_observe(base_clone)
    report = verify_report(base_clone, opencode, 'verify-observation', OBSERVE_KEY)
    assert findings(report, 'CRITICAL') == [], f'no CRITICAL\n{report}'
    assert re.search('outstanding observations', report, re.I), f'outstanding listed\n{report}'
    assert OBSERVATION in report or 'Task 2' in report, f'observation named\n{report}'


def test_verify_accepts_earlier_ci_run(base_clone: Clone, opencode: Start) -> None:
    """A CI job cited on an earlier commit is evidence; no run on the current head is needed."""
    add_ci(base_clone)
    report = verify_report(base_clone, opencode, 'verify-ci-evidence', CI_KEY)
    assert findings(report, 'CRITICAL') == [], f'no CRITICAL\n{report}'


def test_verify_ignores_unaddressed_weakness(base_clone: Clone, opencode: Start) -> None:
    """A weakness the plan's contract does not address is neither a CRITICAL nor a WARNING."""
    add_weak(base_clone)
    report = verify_report(base_clone, opencode, 'verify-weakness', WEAK_KEY)
    assert findings(report, 'CRITICAL') == [], f'no CRITICAL\n{report}'
    assert findings(report, 'WARNING') == [], f'no WARNING\n{report}'


def test_verify_content_check_is_not_coverage(base_clone: Clone, opencode: Start) -> None:
    """A scenario only a check of file contents covers is reported as uncovered."""
    add_cover(base_clone)
    report = verify_report(base_clone, opencode, 'verify-content-check', COVER_KEY)
    assert findings(report, 'WARNING'), f'a WARNING\n{report}'
    assert SCENARIO in report, f'the uncovered scenario named\n{report}'


def test_ship_waits_for_observation(base_clone: Clone, opencode: Start) -> None:
    """Ship refuses a plan whose only open task is a post-merge observation."""
    head = add_observe(base_clone)
    transcript = run(opencode(base_clone), 'ship-observation', 'agentdev:iwe-ship', OBSERVE_KEY)
    reports = agent_results(transcript, SHIPPER)
    assert len(reports) == 1, f'one iwe-shipper report\n{transcript.excerpt("subagent")}'
    assert lead(reports[0]).startswith('Blocked'), f'Blocked\n{reports[0]}'
    assert OBSERVATION in reports[0] or 'Task 2' in reports[0], f'observation named\n{reports[0]}'
    plan = (base_clone.path / PLANS / f'{Path(OBSERVE_KEY).name}.md').read_text()
    assert re.search(r'^stage:', plan, re.M) is None, f'plan still active\n{transcript.excerpt()}'
    assert base_clone.head() == head, f'no commit\n{transcript.excerpt()}'


def test_implement_files_warning(base_clone: Clone, opencode: Start) -> None:
    """A WARNING whose fix adds work is filed through iwe-capture, not added to the plan."""
    stub_warning_verifier(base_clone)
    transcript = run(opencode(base_clone), 'implement-warning', 'agentdev:iwe-implement', LOOP_KEY)
    dispatches = transcript.excerpt('subagent')
    assert base_clone.loop_done(), f'task ticked, file written\n{transcript.excerpt()}'
    assert agent_prompts(transcript, EVALUATOR) == [], f'no revision\n{dispatches}'
    assert not (base_clone.path / WARNED_WORK).exists(), f'warned work not done\n{dispatches}'
    tasks = TASK_HEADING.findall((base_clone.path / LOOP).read_text())
    assert len(tasks) == 1, f'no task added: {tasks}\n{transcript.excerpt()}'
    assert mentions(transcript.calls('skill'), 'iwe-capture'), (
        f'filed\n{transcript.excerpt("skill")}'
    )


def test_plan_leaves_ci_to_merge_gate(base_clone: Clone, opencode: Start) -> None:
    """A plan whose change CI checks carries no task or step claiming that CI passes."""
    plan = written_plan(base_clone, opencode, 'plan-ci', PLAN_CI)
    assert ci_pass_steps(plan) == [], f'no CI-passes step\n{plan}'


def test_plan_marks_post_merge_observation(base_clone: Clone, opencode: Start) -> None:
    """Behaviour visible only after merge becomes a task with a Closed by line."""
    plan = written_plan(base_clone, opencode, 'plan-observe', PLAN_OBSERVE)
    assert '**Closed by:**' in plan, f'observation task\n{plan}'


def test_plan_scopes_leftover_search(base_clone: Clone, opencode: Start) -> None:
    """A verification search for leftover text covers only the files the plan changes."""
    plan = written_plan(base_clone, opencode, 'plan-rename', PLAN_RENAME)
    assert unscoped_searches(plan) == [], f'searches scoped: {unscoped_searches(plan)}\n{plan}'


def test_plan_checks_requirement_against_code(base_clone: Clone, opencode: Start) -> None:
    """Plan writes no requirement the code it describes does not hold."""
    transcript, plans = plan_run(base_clone, opencode, 'plan-contradict', PLAN_CONTRADICT)
    for path in plans:
        plan = path.read_text()
        assert not claims_inside_only(plan) or 'bin/publish-e2e.sh' in planned_files(plan), (
            f'publish writes beside the clone, so no "only inside" claim\n{plan}'
        )


def test_plan_keeps_verification_runnable(base_clone: Clone, opencode: Start) -> None:
    """A check that needs a started Dev Container leaves Verification for an observation or CI."""
    plan = written_plan(base_clone, opencode, 'plan-devcontainer', PLAN_DEVCONTAINER)
    assert 'agentdev-runtime doctor' not in section(plan, 'Verification'), (
        f'not in Verification\n{plan}'
    )
    assert '**Closed by:**' in plan or 'CI job' in plan, f'observation or CI job\n{plan}'


def test_plan_names_mechanism_limit(base_clone: Clone, opencode: Start) -> None:
    """A requirement names what its mechanism does not stop."""
    plan = written_plan(base_clone, opencode, 'plan-limit', PLAN_LIMIT)
    assert names_limit(plan), f'limit named in Spec changes\n{plan}'
