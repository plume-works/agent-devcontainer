"""Ship, Implement, and Explore on Claude Code, one clone per scenario."""

from clone import Clone
from harness_claude import ClaudeTranscript, run_claude
import pytest
from scenarios import (
    APPROVAL,
    CLAUDE_BUDGET,
    EXPLORE,
    GREET_KEY,
    HELLO_KEY,
    mentions,
    PLANTED,
    RULEBOOK,
    WORKFLOW_SKILL,
)

pytestmark = pytest.mark.e2e


def run(clone: Clone, name: str, prompt: str) -> ClaudeTranscript:
    """Run one prompt and assert, first, that the run completed."""
    transcript = run_claude(clone, name, prompt, CLAUDE_BUDGET)
    if transcript.timed_out:
        reason = f'budget exhausted: still running after {CLAUDE_BUDGET}s, killed'
    else:
        reason = f'no result event (claude exited {transcript.returncode})'
    assert transcript.completed() and not transcript.timed_out, (
        f'claude run did not complete: {reason}\n{transcript.excerpt()}'
    )
    return transcript


def test_ship(base_clone: Clone) -> None:
    """Ship without approval dispatches the shipper once and publishes nothing."""
    transcript = run(base_clone, 'ship', f'/agentdev:iwe-ship {HELLO_KEY}')
    prompts = transcript.shipper_prompts()
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
    prompts = transcript.shipper_prompts()
    dispatches = transcript.excerpt('Agent')
    assert len(prompts) == 1, f'one iwe-shipper dispatch\n{dispatches}'
    assert APPROVAL in '\n'.join(prompts), f'approval quoted verbatim\n{dispatches}'
    assert PLANTED not in '\n'.join(prompts), f'planted sentence left out\n{dispatches}'
    assert base_clone.has_marker(), f'publish ran\n{transcript.excerpt()}'
    assert base_clone.plan_done(), f'plan done\n{transcript.excerpt()}'
    assert base_clone.unreleased_diff() == '', (
        f'internal plan adds no release entry\n{base_clone.unreleased_diff()}'
    )


def test_ship_all(base_clone: Clone) -> None:
    """Ship-all dispatches the shipper once for the one shippable plan."""
    transcript = run(base_clone, 'ship-all', f'/agentdev:iwe-ship-all — {APPROVAL}')
    assert len(transcript.shipper_prompts()) == 1, (
        f'one iwe-shipper dispatch\n{transcript.excerpt("Agent")}'
    )


def test_implement(base_clone: Clone) -> None:
    """Implement reads its rulebook in session and dispatches nothing."""
    transcript = run(base_clone, 'implement', f'/agentdev:iwe-implement {GREET_KEY}')
    assert mentions(transcript.calls('Read'), RULEBOOK), (
        f'rulebook read in session\n{transcript.excerpt("Read")}'
    )
    assert transcript.calls('Agent') == [], f'nothing dispatched\n{transcript.excerpt("Agent")}'
    assert base_clone.greet_untouched(), f'task unticked, file absent\n{transcript.excerpt()}'


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
