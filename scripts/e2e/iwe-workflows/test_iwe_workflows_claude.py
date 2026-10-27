"""Verify, Ship, Implement, and Explore on Claude Code, one clone per scenario."""

from clone import Clone, CONFLICT, REVISE
from harness_claude import ClaudeTranscript, run_claude
import pytest
from scenarios import (
    APPROVAL,
    BRANCH_KEY,
    BRANCH_WORK,
    CLAUDE_BUDGET,
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
    PLANTED,
    REVISE_KEY,
    RULEBOOK,
    SHIPPER,
    verdict,
    VERIFIER,
    WORKFLOW_SKILL,
)

pytestmark = pytest.mark.e2e


def run(clone: Clone, name: str, prompt: str) -> ClaudeTranscript:
    """Run one prompt and assert, first, that the run completed."""
    transcript = run_claude(clone, name, prompt, CLAUDE_BUDGET)
    assert transcript.completed() and not transcript.timed_out, (
        'claude run did not complete: '
        f'{transcript.failure_reason(CLAUDE_BUDGET)}\n{transcript.excerpt()}'
    )
    return transcript


def test_verify(base_clone: Clone) -> None:
    """Verify without approval dispatches the verifier once and changes nothing."""
    transcript = run(base_clone, 'verify', f'/agentdev:iwe-verify {HELLO_KEY}')
    prompts = transcript.agent_prompts(VERIFIER)
    dispatches = transcript.excerpt('Agent')
    assert len(prompts) == 1, f'one iwe-verifier dispatch\n{dispatches}'
    assert HELLO_KEY in '\n'.join(prompts), f'prompt names the plan\n{dispatches}'
    assert not base_clone.has_marker(), f'publish did not run\n{transcript.excerpt()}'
    assert base_clone.head() == base_clone.start, f'no commit\n{transcript.excerpt()}'
    assert base_clone.plan_active(), f'plan still active\n{transcript.excerpt()}'


def test_verify_approved(base_clone: Clone) -> None:
    """Approved Verify quotes only the approval, publishes, and still changes no state."""
    prompt = f'/agentdev:iwe-verify {HELLO_KEY} — {APPROVAL} {PLANTED}'
    transcript = run(base_clone, 'verify-approved', prompt)
    prompts = transcript.agent_prompts(VERIFIER)
    dispatches = transcript.excerpt('Agent')
    assert len(prompts) == 1, f'one iwe-verifier dispatch\n{dispatches}'
    assert APPROVAL in '\n'.join(prompts), f'approval quoted verbatim\n{dispatches}'
    assert PLANTED not in '\n'.join(prompts), f'planted sentence left out\n{dispatches}'
    assert base_clone.has_marker(), f'publish ran\n{transcript.excerpt()}'
    assert base_clone.head() == base_clone.start, f'no commit\n{transcript.excerpt()}'
    assert base_clone.plan_active(), f'plan still active\n{transcript.excerpt()}'


def test_ship(base_clone: Clone) -> None:
    """Ship without approval dispatches the shipper once and publishes nothing."""
    transcript = run(base_clone, 'ship', f'/agentdev:iwe-ship {HELLO_KEY}')
    prompts = transcript.agent_prompts(SHIPPER)
    dispatches = transcript.excerpt('Agent')
    assert len(prompts) == 1, f'one iwe-shipper dispatch\n{dispatches}'
    assert HELLO_KEY in '\n'.join(prompts), f'prompt names the plan\n{dispatches}'
    assert not base_clone.has_marker(), f'publish did not run\n{transcript.excerpt()}'
    assert base_clone.head() == base_clone.start, f'no commit\n{transcript.excerpt()}'
    assert base_clone.plan_active(), f'plan still active\n{transcript.excerpt()}'


def test_ship_approved(base_clone: Clone) -> None:
    """Approved Ship quotes only the approval, publishes, and ships the internal plan."""
    prompt = f'/agentdev:iwe-ship {HELLO_KEY} — {APPROVAL} {PLANTED}'
    transcript = run(base_clone, 'ship-approved', prompt)
    prompts = transcript.agent_prompts(SHIPPER)
    dispatches = transcript.excerpt('Agent')
    assert len(prompts) == 1, f'one iwe-shipper dispatch\n{dispatches}'
    assert APPROVAL in '\n'.join(prompts), f'approval quoted verbatim\n{dispatches}'
    assert PLANTED not in '\n'.join(prompts), f'planted sentence left out\n{dispatches}'
    assert base_clone.has_marker(), f'publish ran\n{transcript.excerpt()}'
    assert base_clone.plan_done(), f'plan done\n{transcript.excerpt()}'
    assert base_clone.unreleased_diff() == '', (
        f'internal plan adds no release entry\n{base_clone.unreleased_diff()}'
    )
    assert transcript.agent_prompts(VERIFIER) == [], f'Verify ran in place\n{dispatches}'


def test_ship_all(base_clone: Clone) -> None:
    """Ship-all dispatches the shipper once for the one shippable plan."""
    transcript = run(base_clone, 'ship-all', f'/agentdev:iwe-ship-all — {APPROVAL}')
    assert len(transcript.agent_prompts(SHIPPER)) == 1, (
        f'one iwe-shipper dispatch\n{transcript.excerpt("Agent")}'
    )


def test_implement(base_clone: Clone) -> None:
    """Implement reads its rulebook in session and dispatches nothing."""
    transcript = run(base_clone, 'implement', f'/agentdev:iwe-implement {GREET_KEY}')
    assert mentions(transcript.calls('Read'), RULEBOOK), (
        f'rulebook read in session\n{transcript.excerpt("Read")}'
    )
    assert transcript.calls('Agent') == [], f'nothing dispatched\n{transcript.excerpt("Agent")}'
    assert transcript.agent_prompts(EVALUATOR) == [], (
        f'no evaluator\n{transcript.excerpt("Agent")}'
    )
    assert base_clone.greet_untouched(), f'task unticked, file absent\n{transcript.excerpt()}'
    assert base_clone.branch() == FIXTURE_BRANCH, (
        f'stayed on {FIXTURE_BRANCH}\n{transcript.excerpt()}'
    )
    assert base_clone.local_branches() == [FIXTURE_BRANCH], (
        f'no branch added\n{transcript.excerpt()}'
    )


def test_implement_verifies(base_clone: Clone) -> None:
    """Implement closes the task, then dispatches the verifier once and no evaluator."""
    transcript = run(base_clone, 'implement-verifies', f'/agentdev:iwe-implement {LOOP_KEY}')
    dispatches = transcript.excerpt('Agent')
    assert len(transcript.agent_prompts(VERIFIER)) == 1, f'one iwe-verifier dispatch\n{dispatches}'
    assert transcript.agent_prompts(EVALUATOR) == [], f'no evaluator\n{dispatches}'
    assert base_clone.loop_done(), (
        f'task ticked with evidence, file written\n{transcript.excerpt()}'
    )


def test_implement_revises(base_clone: Clone) -> None:
    """Implement takes an evaluated revision that adds the missing task, then completes it."""
    transcript = run(base_clone, 'implement-revises', f'/agentdev:iwe-implement {REVISE_KEY}')
    prompts = transcript.agent_prompts(EVALUATOR)
    dispatches = transcript.excerpt('Agent')
    assert len(prompts) == 1, f'one iwe-revision-evaluator dispatch\n{dispatches}'
    assert REVISE_KEY in prompts[0], f'prompt names the plan\n{dispatches}'
    before, after = base_clone.revise_tasks_committed()
    assert after > before, f'a task added in a commit: {before} -> {after}\n{transcript.excerpt()}'
    assert base_clone.revise_files(), f'both files written\n{transcript.excerpt()}'


def test_implement_all(loop_only_clone: Clone) -> None:
    """Implement-all dispatches the implementer, then runs the loop's verifier itself."""
    clone = loop_only_clone
    transcript = run(clone, 'implement-all', '/agentdev:iwe-implement-all')
    prompts = transcript.agent_prompts(IMPLEMENTER)
    dispatches = transcript.excerpt('Agent')
    assert len(prompts) == 1, f'one iwe-implementer dispatch\n{dispatches}'
    assert LOOP_KEY in prompts[0], f'prompt names the plan\n{dispatches}'
    assert len(transcript.agent_prompts(VERIFIER)) == 1, f'one iwe-verifier dispatch\n{dispatches}'
    assert transcript.agent_prompts(EVALUATOR) == [], f'no evaluator\n{dispatches}'
    assert clone.loop_done(), f'task ticked with evidence, file written\n{transcript.excerpt()}'


@pytest.mark.parametrize(
    ('variant', 'expected'), [('narrowed', 'ESCALATE'), ('restated', 'REJECT')]
)
def test_evaluator(base_clone: Clone, variant: str, expected: str) -> None:
    """The evaluator escalates a narrowing and rejects a restatement, editing nothing."""
    base_clone.draft_revision(variant)
    transcript = run(base_clone, f'evaluator-{variant}', EVALUATE)
    reports = transcript.agent_results(EVALUATOR)
    dispatches = transcript.excerpt('Agent')
    assert len(reports) == 1, f'one iwe-revision-evaluator report\n{dispatches}'
    assert verdict(reports[0]) == expected, f'{expected}\n{reports[0]}'
    assert base_clone.revision_kept(variant), f'draft left as it was\n{transcript.excerpt()}'
    assert base_clone.head() == base_clone.start, f'no commit\n{transcript.excerpt()}'


def test_implement_stops_on_rejection(stub_evaluator_clone: Clone) -> None:
    """A rejected revision is restored from HEAD and the run stops short of the missing task."""
    clone = stub_evaluator_clone
    transcript = run(clone, 'implement-rejected', f'/agentdev:iwe-implement {REVISE_KEY}')
    dispatches = transcript.excerpt('Agent')
    assert len(transcript.agent_prompts(EVALUATOR)) == 1, f'one evaluator, no retry\n{dispatches}'
    assert clone.intent_kept(REVISE), f'plan restored\n{clone.status()}\n{transcript.excerpt()}'
    assert clone.status() == '', f'clean tree\n{clone.status()}'
    assert not clone.revise_notes_written(), f'no coding past the gap\n{transcript.excerpt()}'


def test_implement_stops_on_narrowing(base_clone: Clone) -> None:
    """A plan only a narrowing could complete stops for the user with its intent unchanged."""
    transcript = run(base_clone, 'implement-narrowing', f'/agentdev:iwe-implement {CONFLICT_KEY}')
    verdicts = [verdict(report) for report in transcript.agent_results(EVALUATOR)]
    assert 'APPROVE' not in verdicts, f'no approved narrowing: {verdicts}\n{transcript.excerpt()}'
    assert base_clone.intent_kept(CONFLICT), (
        f'intent unchanged\n{base_clone.status()}\n{transcript.excerpt()}'
    )
    assert base_clone.conflict_text() in (None, 'yes', 'no'), (
        f'no file satisfying both by trickery: {base_clone.conflict_text()!r}'
    )


def test_implement_on_main(main_clone: Clone) -> None:
    """Implement on main names its work branch through iwe-branch-name and pushes it."""
    transcript = run(main_clone, 'implement-on-main', f'/agentdev:iwe-implement {BRANCH_KEY}')
    assert main_clone.branch() == BRANCH_WORK, f'on {BRANCH_WORK}\n{transcript.excerpt()}'
    assert main_clone.remote_has(BRANCH_WORK), f'pushed to origin\n{transcript.excerpt()}'
    assert 'head:impl/e2e-branch/' in main_clone.gh_calls(), (
        f'named through iwe-branch-name\n{main_clone.gh_calls()}\n{transcript.excerpt()}'
    )


def test_explore(open_question_clone: Clone) -> None:
    """Explore of a finished-sounding plan neither ships, implements, commits, nor edits."""
    clone = open_question_clone
    transcript = run(clone, 'explore', f'/agentdev:iwe-explore {EXPLORE}')
    assert transcript.calls('Agent') == [], f'nothing dispatched\n{transcript.excerpt("Agent")}'
    assert not mentions(transcript.calls('Skill'), WORKFLOW_SKILL), (
        f'no Ship or Implement skill\n{transcript.excerpt("Skill")}'
    )
    assert not clone.has_marker(), f'publish did not run\n{transcript.excerpt()}'
    assert clone.head() == clone.start, f'no commit\n{transcript.excerpt()}'
    assert clone.status() == '', f'clean tree\n{clone.status()}'
