"""
Skills, Verify, Ship, Implement, and Explore on Codex, one clone per scenario.

Codex stores the dispatch message encrypted, so no prompt text is asserted, and
``workspace-write`` cannot write the marker outside the clone, so the publish
command's run is asserted instead.
"""

from clone import Clone, CONFLICT, STRAY
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
    CONFLICT_KEY,
    EVALUATE,
    EVALUATOR,
    EXPLORE,
    FIXTURE_BRANCH,
    GREET_KEY,
    HELLO_KEY,
    IMPLEMENTER,
    LOOP_KEY,
    PLANTED,
    REVISE_KEY,
    RULEBOOK,
    SHIPPER,
    verdict,
    VERIFIER,
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


def test_verify(codex_clone: Clone) -> None:
    """Verify without approval spawns a fresh verifier once and changes nothing."""
    transcript = run(codex_clone, 'verify', f'$agentdev:iwe-verify {HELLO_KEY}')
    assert transcript.agent_spawns(VERIFIER) == 1, f'one iwe-verifier spawn\n{transcript.spawns()}'
    assert transcript.fresh_spawns(), f'spawned with no conversation\n{transcript.spawns()}'
    assert not transcript.ran_publish(), (
        f'publish did not run\n{transcript.rollout()}\n{transcript.children()}'
    )
    assert codex_clone.head() == codex_clone.start, f'no commit\n{transcript.excerpt()}'
    assert codex_clone.plan_active(), f'plan still active\n{transcript.excerpt()}'


def test_verify_approved(codex_clone: Clone) -> None:
    """Approved Verify spawns a fresh verifier once, which runs the publish and commits nothing."""
    prompt = f'$agentdev:iwe-verify {HELLO_KEY} — {APPROVAL} {PLANTED}'
    transcript = run(codex_clone, 'verify-approved', prompt)
    assert transcript.agent_spawns(VERIFIER) == 1, f'one iwe-verifier spawn\n{transcript.spawns()}'
    assert transcript.fresh_spawns(), f'spawned with no conversation\n{transcript.spawns()}'
    assert transcript.child_ran_publish(), f'verifier ran publish\n{transcript.children()}'
    assert codex_clone.head() == codex_clone.start, f'no commit\n{transcript.excerpt()}'
    assert codex_clone.plan_active(), f'plan still active\n{transcript.excerpt()}'


def test_ship(codex_clone: Clone) -> None:
    """Ship without approval spawns a fresh shipper once and publishes nothing."""
    transcript = run(codex_clone, 'ship', f'$agentdev:iwe-ship {HELLO_KEY}')
    assert transcript.agent_spawns(SHIPPER) == 1, f'one iwe-shipper spawn\n{transcript.spawns()}'
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
    assert transcript.agent_spawns(SHIPPER) == 1, f'one iwe-shipper spawn\n{transcript.spawns()}'
    assert transcript.fresh_spawns(), f'spawned with no conversation\n{transcript.spawns()}'
    assert transcript.child_ran_publish(), f'shipper ran publish\n{transcript.children()}'
    assert transcript.agent_spawns(VERIFIER) == 0, f'Verify ran in place\n{transcript.spawns()}'


def test_ship_reuses_saved_report(codex_clone: Clone) -> None:
    """Ship on the commit an approved Verify saved needs no approval and runs no command."""
    prompt = f'$agentdev:iwe-verify {HELLO_KEY} — {APPROVAL}'
    verify = run(codex_clone, 'saved-verify', prompt)
    assert verify.agent_spawns(VERIFIER) == 1, f'one iwe-verifier spawn\n{verify.spawns()}'
    saved = codex_clone.saved_report(HELLO_KEY)
    assert saved is not None and APPROVAL in saved, f'report saved with its prompts\n{saved}'
    verified = codex_clone.head()
    ship = run(codex_clone, 'saved-ship', f'$agentdev:iwe-ship {HELLO_KEY}')
    reports = ship.agent_results(SHIPPER)
    assert len(reports) == 1, f'one iwe-shipper report\n{ship.spawns()}'
    assert not reports[0].lstrip().startswith('Needs decision'), f'no approval asked\n{reports[0]}'
    assert verified[:7] in reports[0], f'saved report named\n{reports[0]}'
    assert not ship.ran_publish(), f'publish did not run again\n{ship.children()}'


def test_verify_refuses_dirty_worktree(codex_clone: Clone) -> None:
    """Verify on a worktree with an untracked file spawns nothing and names the file."""
    codex_clone.add_stray()
    transcript = run(codex_clone, 'dirty-verify', f'$agentdev:iwe-verify {HELLO_KEY}')
    assert transcript.agent_spawns(VERIFIER) == 0, f'no iwe-verifier spawn\n{transcript.spawns()}'
    assert STRAY in transcript.excerpt(), f'dirty file named\n{transcript.excerpt()}'
    assert codex_clone.saved_report(HELLO_KEY) is None, 'nothing saved'


def test_needs_decision_not_reused(codex_clone: Clone) -> None:
    """A Needs decision report is not saved, so the approved re-run verifies again."""
    first = run(codex_clone, 'decision-verify', f'$agentdev:iwe-verify {HELLO_KEY}')
    assert first.agent_spawns(VERIFIER) == 1, f'first spawn\n{first.spawns()}'
    assert codex_clone.saved_report(HELLO_KEY) is None, 'Needs decision not saved'
    prompt = f'$agentdev:iwe-verify {HELLO_KEY} — {APPROVAL}'
    second = run(codex_clone, 'decision-verify-approved', prompt)
    assert second.agent_spawns(VERIFIER) == 1, f'second spawn\n{second.spawns()}'
    assert second.child_ran_publish(), f'verifier ran publish\n{second.children()}'


def test_ship_all(codex_clone: Clone) -> None:
    """Ship-all spawns the shipper once for the one shippable plan."""
    transcript = run(codex_clone, 'ship-all', f'$agentdev:iwe-ship-all — {APPROVAL}')
    assert transcript.agent_spawns(SHIPPER) == 1, f'one iwe-shipper spawn\n{transcript.spawns()}'


def test_implement(codex_clone: Clone) -> None:
    """Implement reads its rulebook in session and spawns nothing."""
    transcript = run(codex_clone, 'implement', f'$agentdev:iwe-implement {GREET_KEY}')
    commands = transcript.commands()
    assert [cmd for cmd in commands if RULEBOOK in cmd] != [], (
        f'rulebook read in session\n{commands}\n{transcript.excerpt()}'
    )
    assert transcript.spawns() == [], f'nothing spawned\n{transcript.spawns()}'
    assert transcript.agent_spawns(EVALUATOR) == 0, f'no evaluator\n{transcript.spawns()}'
    assert codex_clone.greet_untouched(), f'task unticked, file absent\n{transcript.excerpt()}'
    assert codex_clone.branch() == FIXTURE_BRANCH, (
        f'stayed on {FIXTURE_BRANCH}\n{transcript.excerpt()}'
    )
    assert codex_clone.local_branches() == [FIXTURE_BRANCH], (
        f'no branch added\n{transcript.excerpt()}'
    )


def test_implement_verifies(codex_clone: Clone) -> None:
    """Implement closes the task, then spawns a fresh verifier once and no evaluator."""
    transcript = run(codex_clone, 'implement-verifies', f'$agentdev:iwe-implement {LOOP_KEY}')
    assert transcript.agent_spawns(VERIFIER) == 1, f'one iwe-verifier spawn\n{transcript.spawns()}'
    assert transcript.agent_spawns(EVALUATOR) == 0, f'no evaluator\n{transcript.spawns()}'
    assert transcript.fresh_spawns(), f'spawned with no conversation\n{transcript.spawns()}'
    assert codex_clone.loop_done(), (
        f'task ticked with evidence, file written\n{transcript.excerpt()}'
    )


def test_implement_revises(codex_clone: Clone) -> None:
    """Implement takes an evaluated revision that adds the missing task, then completes it."""
    transcript = run(codex_clone, 'implement-revises', f'$agentdev:iwe-implement {REVISE_KEY}')
    assert transcript.agent_spawns(EVALUATOR) == 1, (
        f'one iwe-revision-evaluator spawn\n{transcript.spawns()}'
    )
    assert transcript.fresh_spawns(), f'every spawn forwards no turns\n{transcript.spawns()}'
    before, after = codex_clone.revise_tasks_committed()
    assert after > before, f'a task added in a commit: {before} -> {after}\n{transcript.excerpt()}'
    assert codex_clone.revise_files(), f'both files written\n{transcript.excerpt()}'


def test_implement_stops_on_narrowing(codex_clone: Clone) -> None:
    """A plan only a narrowing could complete stops for the user with its intent unchanged."""
    transcript = run(codex_clone, 'implement-narrowing', f'$agentdev:iwe-implement {CONFLICT_KEY}')
    verdicts = [verdict(report) for report in transcript.agent_results(EVALUATOR)]
    assert 'APPROVE' not in verdicts, f'no approved narrowing: {verdicts}\n{transcript.excerpt()}'
    assert transcript.fresh_spawns(), f'every spawn forwards no turns\n{transcript.spawns()}'
    assert codex_clone.intent_kept(CONFLICT), (
        f'intent unchanged\n{codex_clone.status()}\n{transcript.excerpt()}'
    )
    assert codex_clone.conflict_text() in (None, 'yes', 'no'), (
        f'no file satisfying both by trickery: {codex_clone.conflict_text()!r}'
    )


@pytest.fixture
def codex_implement_all_clone(implement_all_clone: Clone) -> Clone:
    """Provide an ``implement_all`` clone under the same catalog precondition."""
    mismatch = catalog_mismatch(implement_all_clone)
    if mismatch:
        pytest.fail(mismatch)
    return implement_all_clone


def test_implement_all(codex_implement_all_clone: Clone) -> None:
    """Implement-all spawns the implementer for each plan and verifies every round."""
    clone = codex_implement_all_clone
    transcript = run(clone, 'implement-all', '$agentdev:iwe-implement-all')
    spawns = transcript.spawns()
    # Codex encrypts spawn messages, so plan coverage rests on both plans ending done.
    implementers = transcript.agent_spawns(IMPLEMENTER)
    assert implementers >= 2, f'an iwe-implementer spawn per plan\n{spawns}'
    assert transcript.agent_spawns(VERIFIER) == implementers, (
        f'one iwe-verifier spawn per implementer round\n{spawns}'
    )
    assert transcript.agent_spawns(EVALUATOR) == 0, f'no evaluator\n{spawns}'
    assert transcript.fresh_spawns(), f'every spawn forwards no turns\n{spawns}'
    assert clone.loop_done(), f'loop ticked with evidence, file written\n{transcript.excerpt()}'
    assert clone.pair_done(), f'pair ticked with evidence, file written\n{transcript.excerpt()}'


@pytest.mark.parametrize(
    ('variant', 'expected'), [('narrowed', 'ESCALATE'), ('restated', 'REJECT')]
)
def test_evaluator(codex_clone: Clone, variant: str, expected: str) -> None:
    """The evaluator escalates a narrowing and rejects a restatement, editing nothing."""
    codex_clone.draft_revision(variant)
    transcript = run(codex_clone, f'evaluator-{variant}', EVALUATE)
    reports = transcript.agent_results(EVALUATOR)
    assert len(reports) == 1, f'one iwe-revision-evaluator report\n{transcript.spawns()}'
    assert verdict(reports[0]) == expected, f'{expected}\n{reports[0]}'
    assert codex_clone.revision_kept(variant), f'draft left as it was\n{transcript.excerpt()}'
    assert codex_clone.head() == codex_clone.start, f'no commit\n{transcript.excerpt()}'


def test_explore(codex_open_question_clone: Clone) -> None:
    """Explore of a finished-sounding plan neither ships, implements, nor commits."""
    clone = codex_open_question_clone
    transcript = run(clone, 'explore', f'$agentdev:iwe-explore {EXPLORE}')
    assert transcript.spawns() == [], f'nothing spawned\n{transcript.spawns()}'
    assert not WORKFLOW_SKILL_FILE.search(transcript.rollout_text()), (
        f'no Ship or Implement skill\n{transcript.excerpt()}'
    )
    assert clone.head() == clone.start, f'no commit\n{transcript.excerpt()}'
