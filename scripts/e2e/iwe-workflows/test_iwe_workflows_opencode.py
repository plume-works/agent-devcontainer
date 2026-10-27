"""Verify, Ship, Implement, and Explore on OpenCode, one isolated server per scenario."""

from clone import Clone, CONFLICT, REVISE
from harness_opencode import OpenCodeServer, PROMPT_COMMAND, Transcript
import pytest
from scenarios import (
    APPROVAL,
    BRANCH_KEY,
    BRANCH_WORK,
    CONFLICT_KEY,
    EVALUATE,
    EVALUATOR,
    EXPLORE,
    FIXTURE_BRANCH,
    GREET_KEY,
    HELLO_KEY,
    IMPLEMENTER,
    LOOP_KEY,
    mentions,
    OPENCODE_BUDGET,
    PLANTED,
    REVISE_KEY,
    RULEBOOK,
    SHIPPER,
    verdict,
    VERIFIER,
    WORKFLOW_SKILL,
)

pytestmark = pytest.mark.e2e


def run(server: OpenCodeServer, name: str, command: str, text: str) -> Transcript:
    """Run one command and assert, first, that the run completed on a working login."""
    transcript = server.run(name, command, text, OPENCODE_BUDGET)
    reason = transcript.failure_reason(OPENCODE_BUDGET)
    assert reason is None, f'opencode run did not complete: {reason}\n{transcript.excerpt()}'
    return transcript


def agent_prompts(transcript: Transcript, agent: str) -> list[str]:
    """Return the prompt of every dispatch of the catalog agent ``agent``."""
    calls = transcript.calls('subagent')
    return [str(call.get('prompt', '')) for call in calls if call.get('agent') == agent]


def agent_results(transcript: Transcript, agent: str) -> list[str]:
    """Return the report of every finished dispatch of the catalog agent ``agent``."""
    return [
        '\n'.join(item.get('text', '') for item in state.get('content') or [])
        for part in transcript.assistant_parts()
        if part.get('type') == 'tool' and part.get('name') == 'subagent'
        for state in [part.get('state') or {}]
        if (state.get('input') or {}).get('agent') == agent and state.get('status') == 'completed'
    ]


def test_verify(base_clone: Clone, opencode) -> None:
    """Verify without approval dispatches the verifier once and changes nothing."""
    transcript = run(opencode(base_clone), 'verify', 'agentdev:iwe-verify', HELLO_KEY)
    prompts = agent_prompts(transcript, VERIFIER)
    dispatches = transcript.excerpt('subagent')
    assert len(prompts) == 1, f'one iwe-verifier dispatch\n{dispatches}'
    assert HELLO_KEY in '\n'.join(prompts), f'prompt names the plan\n{dispatches}'
    assert not base_clone.has_marker(), f'publish did not run\n{transcript.excerpt()}'
    assert base_clone.head() == base_clone.start, f'no commit\n{transcript.excerpt()}'
    assert base_clone.plan_active(), f'plan still active\n{transcript.excerpt()}'


def test_verify_approved(base_clone: Clone, opencode) -> None:
    """Approved Verify quotes only the approval, publishes, and still changes no state."""
    text = f'{HELLO_KEY} — {APPROVAL} {PLANTED}'
    transcript = run(opencode(base_clone), 'verify-approved', 'agentdev:iwe-verify', text)
    prompts = agent_prompts(transcript, VERIFIER)
    dispatches = transcript.excerpt('subagent')
    assert len(prompts) == 1, f'one iwe-verifier dispatch\n{dispatches}'
    assert APPROVAL in '\n'.join(prompts), f'approval quoted verbatim\n{dispatches}'
    assert PLANTED not in '\n'.join(prompts), f'planted sentence left out\n{dispatches}'
    assert base_clone.has_marker(), f'publish ran\n{transcript.excerpt()}'
    assert base_clone.head() == base_clone.start, f'no commit\n{transcript.excerpt()}'
    assert base_clone.plan_active(), f'plan still active\n{transcript.excerpt()}'


def test_ship(base_clone: Clone, opencode) -> None:
    """Ship without approval dispatches the shipper once and publishes nothing."""
    transcript = run(opencode(base_clone), 'ship', 'agentdev:iwe-ship', HELLO_KEY)
    prompts = agent_prompts(transcript, SHIPPER)
    dispatches = transcript.excerpt('subagent')
    assert len(prompts) == 1, f'one iwe-shipper dispatch\n{dispatches}'
    assert HELLO_KEY in '\n'.join(prompts), f'prompt names the plan\n{dispatches}'
    assert not base_clone.has_marker(), f'publish did not run\n{transcript.excerpt()}'
    assert base_clone.head() == base_clone.start, f'no commit\n{transcript.excerpt()}'
    assert base_clone.plan_active(), f'plan still active\n{transcript.excerpt()}'


def test_ship_approved(base_clone: Clone, opencode) -> None:
    """Approved Ship quotes only the approval, publishes, and ships the internal plan."""
    text = f'{HELLO_KEY} — {APPROVAL} {PLANTED}'
    transcript = run(opencode(base_clone), 'ship-approved', 'agentdev:iwe-ship', text)
    prompts = agent_prompts(transcript, SHIPPER)
    dispatches = transcript.excerpt('subagent')
    assert len(prompts) == 1, f'one iwe-shipper dispatch\n{dispatches}'
    assert APPROVAL in '\n'.join(prompts), f'approval quoted verbatim\n{dispatches}'
    assert PLANTED not in '\n'.join(prompts), f'planted sentence left out\n{dispatches}'
    assert base_clone.has_marker(), f'publish ran\n{transcript.excerpt()}'
    assert base_clone.plan_done(), f'plan done\n{transcript.excerpt()}'
    assert base_clone.unreleased_diff() == '', (
        f'internal plan adds no release entry\n{base_clone.unreleased_diff()}'
    )
    assert agent_prompts(transcript, VERIFIER) == [], f'Verify ran in place\n{dispatches}'


def test_ship_all(base_clone: Clone, opencode) -> None:
    """Ship-all dispatches the shipper once for the one shippable plan."""
    transcript = run(opencode(base_clone), 'ship-all', 'agentdev:iwe-ship-all', f'— {APPROVAL}')
    assert len(agent_prompts(transcript, SHIPPER)) == 1, (
        f'one iwe-shipper dispatch\n{transcript.excerpt("subagent")}'
    )


def test_implement(base_clone: Clone, opencode) -> None:
    """Implement reads its rulebook in session and dispatches nothing."""
    transcript = run(opencode(base_clone), 'implement', 'agentdev:iwe-implement', GREET_KEY)
    assert mentions(transcript.calls('read'), RULEBOOK), (
        f'rulebook read in session\n{transcript.excerpt("read")}'
    )
    assert transcript.calls('subagent') == [], (
        f'nothing dispatched\n{transcript.excerpt("subagent")}'
    )
    assert agent_prompts(transcript, EVALUATOR) == [], (
        f'no evaluator\n{transcript.excerpt("subagent")}'
    )
    assert base_clone.greet_untouched(), f'task unticked, file absent\n{transcript.excerpt()}'
    assert base_clone.branch() == FIXTURE_BRANCH, (
        f'stayed on {FIXTURE_BRANCH}\n{transcript.excerpt()}'
    )
    assert base_clone.local_branches() == [FIXTURE_BRANCH], (
        f'no branch added\n{transcript.excerpt()}'
    )


def test_implement_verifies(base_clone: Clone, opencode) -> None:
    """Implement closes the task, then dispatches the verifier once and no evaluator."""
    transcript = run(
        opencode(base_clone), 'implement-verifies', 'agentdev:iwe-implement', LOOP_KEY
    )
    dispatches = transcript.excerpt('subagent')
    assert len(agent_prompts(transcript, VERIFIER)) == 1, (
        f'one iwe-verifier dispatch\n{dispatches}'
    )
    assert agent_prompts(transcript, EVALUATOR) == [], f'no evaluator\n{dispatches}'
    assert base_clone.loop_done(), (
        f'task ticked with evidence, file written\n{transcript.excerpt()}'
    )


def test_implement_revises(base_clone: Clone, opencode) -> None:
    """Implement takes an evaluated revision that adds the missing task, then completes it."""
    transcript = run(
        opencode(base_clone), 'implement-revises', 'agentdev:iwe-implement', REVISE_KEY
    )
    prompts = agent_prompts(transcript, EVALUATOR)
    dispatches = transcript.excerpt('subagent')
    assert len(prompts) == 1, f'one iwe-revision-evaluator dispatch\n{dispatches}'
    assert REVISE_KEY in prompts[0], f'prompt names the plan\n{dispatches}'
    before, after = base_clone.revise_tasks_committed()
    assert after > before, f'a task added in a commit: {before} -> {after}\n{transcript.excerpt()}'
    assert base_clone.revise_files(), f'both files written\n{transcript.excerpt()}'


def test_implement_all(loop_only_clone: Clone, opencode) -> None:
    """Implement-all dispatches the implementer, then runs the loop's verifier itself."""
    clone = loop_only_clone
    transcript = run(opencode(clone), 'implement-all', 'agentdev:iwe-implement-all', '')
    prompts = agent_prompts(transcript, IMPLEMENTER)
    dispatches = transcript.excerpt('subagent')
    assert len(prompts) == 1, f'one iwe-implementer dispatch\n{dispatches}'
    assert LOOP_KEY in prompts[0], f'prompt names the plan\n{dispatches}'
    assert len(agent_prompts(transcript, VERIFIER)) == 1, (
        f'one iwe-verifier dispatch\n{dispatches}'
    )
    assert agent_prompts(transcript, EVALUATOR) == [], f'no evaluator\n{dispatches}'
    assert clone.loop_done(), f'task ticked with evidence, file written\n{transcript.excerpt()}'


@pytest.mark.parametrize(
    ('variant', 'expected'), [('narrowed', 'ESCALATE'), ('restated', 'REJECT')]
)
def test_evaluator(base_clone: Clone, opencode, variant: str, expected: str) -> None:
    """The evaluator escalates a narrowing and rejects a restatement, editing nothing."""
    base_clone.draft_revision(variant)
    transcript = run(opencode(base_clone), f'evaluator-{variant}', PROMPT_COMMAND, EVALUATE)
    reports = agent_results(transcript, EVALUATOR)
    dispatches = transcript.excerpt('subagent')
    assert len(reports) == 1, f'one iwe-revision-evaluator report\n{dispatches}'
    assert verdict(reports[0]) == expected, f'{expected}\n{reports[0]}'
    assert base_clone.revision_kept(variant), f'draft left as it was\n{transcript.excerpt()}'
    assert base_clone.head() == base_clone.start, f'no commit\n{transcript.excerpt()}'


def test_implement_stops_on_rejection(stub_evaluator_clone: Clone, opencode) -> None:
    """A rejected revision is restored from HEAD and the run stops short of the missing task."""
    clone = stub_evaluator_clone
    transcript = run(opencode(clone), 'implement-rejected', 'agentdev:iwe-implement', REVISE_KEY)
    dispatches = transcript.excerpt('subagent')
    assert len(agent_prompts(transcript, EVALUATOR)) == 1, f'one evaluator, no retry\n{dispatches}'
    assert clone.intent_kept(REVISE), f'plan restored\n{clone.status()}\n{transcript.excerpt()}'
    assert clone.status() == '', f'clean tree\n{clone.status()}'
    assert not clone.revise_notes_written(), f'no coding past the gap\n{transcript.excerpt()}'


def test_implement_stops_on_narrowing(base_clone: Clone, opencode) -> None:
    """A plan only a narrowing could complete stops for the user with its intent unchanged."""
    transcript = run(
        opencode(base_clone), 'implement-narrowing', 'agentdev:iwe-implement', CONFLICT_KEY
    )
    verdicts = [verdict(report) for report in agent_results(transcript, EVALUATOR)]
    assert 'APPROVE' not in verdicts, f'no approved narrowing: {verdicts}\n{transcript.excerpt()}'
    assert base_clone.intent_kept(CONFLICT), (
        f'intent unchanged\n{base_clone.status()}\n{transcript.excerpt()}'
    )
    assert base_clone.conflict_text() in (None, 'yes', 'no'), (
        f'no file satisfying both by trickery: {base_clone.conflict_text()!r}'
    )


def test_implement_on_main(main_clone: Clone, opencode) -> None:
    """Implement on main names its work branch through iwe-branch-name and pushes it."""
    transcript = run(
        opencode(main_clone), 'implement-on-main', 'agentdev:iwe-implement', BRANCH_KEY
    )
    assert main_clone.branch() == BRANCH_WORK, f'on {BRANCH_WORK}\n{transcript.excerpt()}'
    assert main_clone.remote_has(BRANCH_WORK), f'pushed to origin\n{transcript.excerpt()}'
    assert 'head:impl/e2e-branch/' in main_clone.gh_calls(), (
        f'named through iwe-branch-name\n{main_clone.gh_calls()}\n{transcript.excerpt()}'
    )


def test_explore(open_question_clone: Clone, opencode) -> None:
    """Explore of a finished-sounding plan neither ships, implements, nor commits."""
    clone = open_question_clone
    transcript = run(opencode(clone), 'explore', 'agentdev:iwe-explore', EXPLORE)
    assert transcript.calls('subagent') == [], (
        f'nothing dispatched\n{transcript.excerpt("subagent")}'
    )
    assert not mentions(transcript.calls('skill'), WORKFLOW_SKILL), (
        f'no Ship or Implement skill\n{transcript.excerpt("skill")}'
    )
    assert not clone.has_marker(), f'publish did not run\n{transcript.excerpt()}'
    assert clone.head() == clone.start, f'no commit\n{transcript.excerpt()}'
