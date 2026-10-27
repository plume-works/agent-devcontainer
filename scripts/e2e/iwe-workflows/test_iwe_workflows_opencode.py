"""Ship, Implement, and Explore on OpenCode, one isolated server per scenario."""

from clone import Clone
from harness_opencode import OpenCodeServer, Transcript
import pytest
from scenarios import (
    APPROVAL,
    BRANCH_KEY,
    BRANCH_WORK,
    EXPLORE,
    FIXTURE_BRANCH,
    GREET_KEY,
    HELLO_KEY,
    mentions,
    OPENCODE_BUDGET,
    PLANTED,
    RULEBOOK,
    SHIPPER,
    WORKFLOW_SKILL,
)

pytestmark = pytest.mark.e2e


def run(server: OpenCodeServer, name: str, command: str, text: str) -> Transcript:
    """Run one command and assert, first, that the run completed on a working login."""
    transcript = server.run(name, command, text, OPENCODE_BUDGET)
    reason = transcript.failure_reason(OPENCODE_BUDGET)
    assert reason is None, f'opencode run did not complete: {reason}\n{transcript.excerpt()}'
    return transcript


def shipper_prompts(transcript: Transcript) -> list[str]:
    """Return the prompt of every ``iwe-shipper`` dispatch."""
    calls = transcript.calls('subagent')
    return [str(call.get('prompt', '')) for call in calls if call.get('agent') == SHIPPER]


def test_ship(base_clone: Clone, opencode) -> None:
    """Ship without approval dispatches the shipper once and publishes nothing."""
    transcript = run(opencode(base_clone), 'ship', 'agentdev:iwe-ship', HELLO_KEY)
    prompts = shipper_prompts(transcript)
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
    prompts = shipper_prompts(transcript)
    dispatches = transcript.excerpt('subagent')
    assert len(prompts) == 1, f'one iwe-shipper dispatch\n{dispatches}'
    assert APPROVAL in '\n'.join(prompts), f'approval quoted verbatim\n{dispatches}'
    assert PLANTED not in '\n'.join(prompts), f'planted sentence left out\n{dispatches}'
    assert base_clone.has_marker(), f'publish ran\n{transcript.excerpt()}'
    assert base_clone.plan_done(), f'plan done\n{transcript.excerpt()}'
    assert base_clone.unreleased_diff() == '', (
        f'internal plan adds no release entry\n{base_clone.unreleased_diff()}'
    )


def test_ship_all(base_clone: Clone, opencode) -> None:
    """Ship-all dispatches the shipper once for the one shippable plan."""
    transcript = run(opencode(base_clone), 'ship-all', 'agentdev:iwe-ship-all', f'— {APPROVAL}')
    assert len(shipper_prompts(transcript)) == 1, (
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
    assert base_clone.greet_untouched(), f'task unticked, file absent\n{transcript.excerpt()}'
    assert base_clone.branch() == FIXTURE_BRANCH, (
        f'stayed on {FIXTURE_BRANCH}\n{transcript.excerpt()}'
    )
    assert base_clone.local_branches() == [FIXTURE_BRANCH], (
        f'no branch added\n{transcript.excerpt()}'
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
