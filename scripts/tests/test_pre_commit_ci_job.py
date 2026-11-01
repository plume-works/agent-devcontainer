"""Tests that pre-commit gates CI in the compose-pinned image and promotion in the candidate."""

from __future__ import annotations

from pathlib import Path
import subprocess

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((REPO_ROOT / '.github/workflows/primary-checks.yml').read_text())
JOB = WORKFLOW['jobs']['pre-commit']
# The committed pin: the Dev Container smoke test patches the working copy to its own build.
COMPOSE = yaml.safe_load(
    subprocess.run(
        ['git', 'show', 'HEAD:devcontainer-compose-pins.yml'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
)


def _run_lines(step: dict[str, object]) -> str:
    """Return a step's run script, or an empty string for a `uses` step."""
    return str(step.get('run', ''))


def test_job_runs_in_the_compose_pinned_image() -> None:
    """The job's image is the devcontainer pin, tag and digest, that compose consumes."""
    assert JOB['container']['image'] == COMPOSE['services']['devcontainer']['image']


def test_steps_run_in_order_one_per_timed_phase() -> None:
    """Checkout, range, uv sync, install-hooks, and run are separate steps, in that order."""
    steps = JOB['steps']
    assert [step.get('uses', '').split('@')[0] for step in steps[:1]] == ['actions/checkout']
    phases = ['pre-commit-ci-range.py', 'uv sync --locked', 'pre-commit install-hooks']
    for step, phase in zip(steps[1:4], phases, strict=True):
        assert phase in _run_lines(step), step
    assert 'pre-commit run' in _run_lines(steps[4])
    assert len(steps) == 5


def test_checkout_fetches_full_history() -> None:
    """The range and gitleaks scan need every commit, so checkout fetches all of history."""
    assert JOB['steps'][0]['with']['fetch-depth'] == 0


def test_run_step_takes_the_range_and_skips_the_branch_guard() -> None:
    """The run step reads the range outputs and skips no-commit-to-branch on main."""
    run = JOB['steps'][4]
    range_id = JOB['steps'][1]['id']
    assert run['env']['SKIP'] == 'no-commit-to-branch'
    for output in ('from_ref', 'to_ref', 'all_files', 'gitleaks_log_opts'):
        assert f'steps.{range_id}.outputs.{output}' in yaml.safe_dump(run['env'])
    assert '--all-files' in run['run']
    assert '--from-ref' in run['run'] and '--to-ref' in run['run']


def test_ci_starts_only_after_pre_commit() -> None:
    """CI/CD needs the pre-commit job, and no reformat job remains."""
    assert 'pre-commit' in WORKFLOW['jobs']['ci']['needs']
    assert 'reformat' not in WORKFLOW['jobs']


CI = yaml.safe_load((REPO_ROOT / '.github/workflows/ci.yml').read_text())
CANDIDATE = CI['jobs']['candidate-pre-commit']


def test_candidate_run_uses_the_image_this_run_built() -> None:
    """The second run's container is the merged candidate, not the committed pin."""
    assert CANDIDATE['needs'] == ['merge-dev-image']
    assert CANDIDATE['container']['image'] == (
        '${{ needs.merge-dev-image.outputs.devcontainer_image_pinned }}'
    )


def test_candidate_run_checks_every_file() -> None:
    """Any rebuilt tool can break any file, so the candidate run never narrows to a range."""
    steps = CANDIDATE['steps']
    assert steps[0]['uses'].split('@')[0] == 'actions/checkout'
    phases = ['uv sync --locked', 'pre-commit install-hooks', 'pre-commit run --all-files']
    for step, phase in zip(steps[1:], phases, strict=True):
        assert phase in _run_lines(step), step
    assert steps[-1]['env']['SKIP'] == 'no-commit-to-branch'


def test_candidate_run_gates_promotion() -> None:
    """No moving tag names an image whose tools fail the hooks."""
    assert 'candidate-pre-commit' in CI['jobs']['promote-dev-image']['needs']
    assert 'candidate-pre-commit' in CI['jobs']['finished']['needs']
