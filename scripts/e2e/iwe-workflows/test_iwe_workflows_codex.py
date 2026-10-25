"""
Skills, Ship, Implement, and Explore on Codex, one clone per scenario.

Codex stores the dispatch message encrypted, so no prompt text is asserted, and
``workspace-write`` cannot write the marker outside the clone, so the publish
command's run is asserted instead.
"""

from clone import Clone
from harness_codex import (
    catalog_mismatch,
    CodexTranscript,
    gated_skills,
    run_codex,
    WORKFLOW_SKILL_FILE,
)
import pytest
from scenarios import (
    APPROVAL,
    CODEX_BUDGET,
    EXPLORE,
    FIXTURE_BRANCH,
    GREET_KEY,
    HELLO_KEY,
    PLANTED,
    RULEBOOK,
)

pytestmark = pytest.mark.e2e


@pytest.fixture
def codex_clone(base_clone: Clone) -> Clone:
    """Provide a ``base`` clone, failing when Codex's installed catalog differs from it."""
    mismatch = catalog_mismatch(base_clone)
    if mismatch:
        pytest.fail(mismatch)
    return base_clone


@pytest.fixture
def codex_open_question_clone(open_question_clone: Clone) -> Clone:
    """Provide an ``open_question`` clone under the same catalog precondition."""
    mismatch = catalog_mismatch(open_question_clone)
    if mismatch:
        pytest.fail(mismatch)
    return open_question_clone


def run(clone: Clone, name: str, prompt: str) -> CodexTranscript:
    """Run one prompt and assert, first, that the run completed."""
    transcript = run_codex(clone, name, prompt, CODEX_BUDGET)
    if transcript.timed_out:
        reason = f'budget exhausted: still running after {CODEX_BUDGET}s, killed'
    else:
        reason = f'no turn.completed event (codex exited {transcript.returncode})'
    assert transcript.completed() and not transcript.timed_out, (
        f'codex run did not complete: {reason}\n{transcript.excerpt()}'
    )
    return transcript


def test_skills(codex_clone: Clone) -> None:
    """No explicit-only skill appears in Codex's implicitly invocable list."""
    prompt = (
        'List the name of every skill in your available-skills list, one per line, '
        'and nothing else. Do not run any command.'
    )
    transcript = run(codex_clone, 'skills', prompt)
    listed = set(transcript.agent_lines())
    invocable = [skill for skill in gated_skills(codex_clone) if f'agentdev:{skill}' in listed]
    assert invocable == [], (
        f'explicit-only skills listed as invocable: {invocable}\n{transcript.excerpt()}'
    )


def test_ship(codex_clone: Clone) -> None:
    """Ship without approval spawns a fresh shipper once and publishes nothing."""
    transcript = run(codex_clone, 'ship', f'$agentdev:iwe-ship {HELLO_KEY}')
    assert transcript.shipper_spawns() == 1, f'one iwe-shipper spawn\n{transcript.spawns()}'
    assert transcript.fresh_spawns(), f'spawned with no conversation\n{transcript.spawns()}'
    assert not transcript.ran_publish(), (
        f'publish did not run\n{transcript.rollout()}\n{transcript.children()}'
    )
    assert codex_clone.head() == codex_clone.start, f'no commit\n{transcript.excerpt()}'
    assert codex_clone.plan_active(), f'plan still active\n{transcript.excerpt()}'


def test_ship_approved(codex_clone: Clone) -> None:
    """Approved Ship spawns a fresh shipper once, and that shipper runs the publish command."""
    prompt = f'$agentdev:iwe-ship {HELLO_KEY} — {APPROVAL} {PLANTED}'
    transcript = run(codex_clone, 'ship-approved', prompt)
    assert transcript.shipper_spawns() == 1, f'one iwe-shipper spawn\n{transcript.spawns()}'
    assert transcript.fresh_spawns(), f'spawned with no conversation\n{transcript.spawns()}'
    assert transcript.child_ran_publish(), f'shipper ran publish\n{transcript.children()}'


def test_ship_all(codex_clone: Clone) -> None:
    """Ship-all spawns the shipper once for the one shippable plan."""
    transcript = run(codex_clone, 'ship-all', f'$agentdev:iwe-ship-all — {APPROVAL}')
    assert transcript.shipper_spawns() == 1, f'one iwe-shipper spawn\n{transcript.spawns()}'


def test_implement(codex_clone: Clone) -> None:
    """Implement reads its rulebook in session and spawns nothing."""
    transcript = run(codex_clone, 'implement', f'$agentdev:iwe-implement {GREET_KEY}')
    commands = transcript.commands()
    assert [cmd for cmd in commands if RULEBOOK in cmd] != [], (
        f'rulebook read in session\n{commands}\n{transcript.excerpt()}'
    )
    assert transcript.spawns() == [], f'nothing spawned\n{transcript.spawns()}'
    assert codex_clone.greet_untouched(), f'task unticked, file absent\n{transcript.excerpt()}'
    assert codex_clone.branch() == FIXTURE_BRANCH, (
        f'stayed on {FIXTURE_BRANCH}\n{transcript.excerpt()}'
    )
    assert codex_clone.local_branches() == [FIXTURE_BRANCH], (
        f'no branch added\n{transcript.excerpt()}'
    )


def test_explore(codex_open_question_clone: Clone) -> None:
    """Explore of a finished-sounding plan neither ships, implements, nor commits."""
    clone = codex_open_question_clone
    transcript = run(clone, 'explore', f'$agentdev:iwe-explore {EXPLORE}')
    assert transcript.spawns() == [], f'nothing spawned\n{transcript.spawns()}'
    assert not WORKFLOW_SKILL_FILE.search(transcript.rollout_text()), (
        f'no Ship or Implement skill\n{transcript.excerpt()}'
    )
    assert clone.head() == clone.start, f'no commit\n{transcript.excerpt()}'
