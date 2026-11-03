"""
Fixtures and predicates for the failures the converging Implement loop removes.

Each setup commits one fixture plan, and the code it claims, on top of a clone's
``base``; the predicates read a Verify or Shipper report, or a plan Plan wrote.
Plan: data/plans/20261102-autonomy-loop.
"""

from pathlib import Path
import re
import shutil

from clone import add_hub_links, Clone, DATA, FIXTURES

OBSERVE_KEY = 'data/plans/20261103-e2e-observe'
CI_KEY = 'data/plans/20261103-e2e-ci'
WEAK_KEY = 'data/plans/20261103-e2e-weak'
COVER_KEY = 'data/plans/20261103-e2e-cover'
VERIFIER_AGENT = '.agents/plugins/agentdev/agents/iwe-verifier.agent.md'
# The work the stub verifier's WARNING asks for; the loop files it instead.
WARNED_WORK = 'bin/check-loop.sh'
OBSERVATION = 'Readers use the observe file'
SCENARIO = 'A name is greeted'
PLANS = f'{DATA}/plans'
# Plan runs here with nobody to answer, so its questions must not stall the run.
UNATTENDED = (
    ' Nobody can answer questions in this run: where you would ask, take the option'
    ' you would recommend and record it in the plan.'
)
PLAN_CI = (
    'Add `bin/lint-e2e.sh`, which exits 0 when `e2e/hello.txt` holds exactly `hello`,'
    ' and a `lint-e2e` job in a new `.github/workflows/lint-e2e.yml` that runs it on'
    ' every pull request.'
)
PLAN_OBSERVE = (
    'Add `.github/workflows/e2e-release.yml`, which attaches `e2e/hello.txt` to every'
    ' GitHub release published from `main`.'
)
PLAN_RENAME = 'Rename `e2e/hello.txt` to `e2e/greeting.txt` and update every reference to it.'
PLAN_CONTRADICT = (
    'Record the existing behaviour of `bin/publish-e2e.sh` as a requirement in a new'
    ' spec `e2e-publish`: it SHALL write only inside the repository. This is'
    ' documentation only; change no code.'
)
PLAN_DEVCONTAINER = (
    'Add `bin/doctor-e2e.sh`, which prints `ok`. The change is proven by running'
    ' `agentdev-runtime doctor` inside a started Dev Container.'
)
PLAN_LIMIT = (
    'Add `bin/integrity-e2e.sh`, which fails when the sha256 digest of `e2e/hello.txt`'
    ' differs from the digest stored in `e2e/hello.sha256`.'
)
_FINDING = re.compile(r'^[\s>*#-]*\**(CRITICAL|WARNING)\**\s*(?:[—:(-]|$)')
_NONE = re.compile(r'\b(none|no findings?)\b|^\W*\w+\W*0\W*$', re.IGNORECASE)
_SEARCH = re.compile(r'\b(git grep|rg|grep\s+-\w*[rR])\b')
_CI_PASSES = re.compile(r'\b(CI|workflow|job|check)s?\b.*\b(pass|passes|green|succeeds?)\b', re.I)
_LIMIT = re.compile(
    r"\b(does not|doesn't|cannot|can't|SHALL NOT|not)\s+(detect|catch|stop|protect|notice|guard)",
    re.IGNORECASE,
)


def _add_plan(clone: Clone, key: str, title: str, files: dict[str, str]) -> str:
    """Commit ``files`` (destination: fixture path), then the plan citing that commit."""
    for destination, source in files.items():
        target = clone.path / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURES / source, target)
    code = clone.commit_all(f'e2e: code for {Path(key).name}')
    name = f'{Path(key).name}.md'
    text = (FIXTURES / 'plans' / name).read_text().replace('{commit}', code[:12])
    (clone.path / PLANS / name).write_text(text)
    add_hub_links(clone.path / DATA / 'plans.md', (f'[{title}](plans/{name})',))
    clone.iwe_check()
    return clone.commit_all(f'e2e: plan {Path(key).name}')


def add_observe(clone: Clone) -> str:
    """Commit the plan whose only open task is a post-merge observation; return ``HEAD``."""
    files = {'e2e/observe.txt': 'e2e/observe.txt'}
    return _add_plan(clone, OBSERVE_KEY, 'E2E observe fixture', files)


def add_ci(clone: Clone) -> str:
    """Commit the CI plan, then move ``HEAD`` past the commit its evidence names."""
    files = {'bin/ci-e2e.sh': 'bin/ci-e2e.sh', '.github/workflows/e2e-ci.yml': 'e2e/e2e-ci.yml'}
    _add_plan(clone, CI_KEY, 'E2E CI fixture', files)
    plan = clone.path / PLANS / f'{Path(CI_KEY).name}.md'
    plan.write_text(
        plan.read_text().replace(
            'end to end.', 'end to end. The job runs on GitHub-hosted runners.', 1
        )
    )
    clone.iwe_check()
    return clone.commit_all('e2e: reword the CI plan after its CI run')


def add_weak(clone: Clone) -> str:
    """Commit the plan whose greeter has a weakness its contract does not address."""
    files = {'bin/greet-e2e.sh': 'bin/greet-e2e.sh'}
    return _add_plan(clone, WEAK_KEY, 'E2E weak fixture', files)


def add_cover(clone: Clone) -> str:
    """Commit the plan whose scenario only a content check covers."""
    files = {'bin/greet-e2e.sh': 'bin/greet-e2e.sh'}
    return _add_plan(clone, COVER_KEY, 'E2E cover fixture', files)


def stub_warning_verifier(clone: Clone) -> str:
    """Replace the catalog verifier with a stub that reports one work-adding WARNING."""
    shutil.copy2(FIXTURES / 'agents/iwe-verifier.warning-stub.md', clone.path / VERIFIER_AGENT)
    return clone.commit_all('e2e: stub verifier reports a WARNING')


def lead(report: str) -> str:
    """Return a report's first non-empty line, without Markdown emphasis or heading marks."""
    first = next((line for line in report.splitlines() if line.strip()), '')
    return re.sub(r'[*#]', '', first).strip()


def findings(report: str, level: str) -> list[str]:
    """Return the report lines that open a ``level`` finding, ignoring 'none' placeholders."""
    return [
        line
        for line in report.splitlines()
        if (found := _FINDING.match(line)) and found.group(1) == level and not _NONE.search(line)
    ]


def new_plans(clone: Clone) -> list[Path]:
    """Return every plan file added since ``clone.start``, committed or not."""
    committed = clone.git(
        'diff', '--name-only', '--diff-filter=A', clone.start, 'HEAD', '--', PLANS
    ).split()
    untracked = clone.git('ls-files', '--others', '--exclude-standard', '--', PLANS).split()
    return [clone.path / name for name in sorted(set(committed + untracked))]


def section(plan: str, heading: str) -> str:
    """Return the body of ``## heading`` in a plan, or an empty string."""
    found = re.search(rf'^## {re.escape(heading)}\n(.*?)(?=^## |\Z)', plan, re.M | re.S)
    return found.group(1) if found else ''


def planned_files(plan: str) -> list[str]:
    """Return every backticked path on the plan's ``**Files:**`` lines."""
    blocks = re.findall(r'^\*\*Files:\*\*(.*?)(?=\n\s*\n)', plan, re.M | re.S)
    return [path for block in blocks for path in re.findall(r'`([^`]+)`', block)]


def ci_pass_steps(plan: str) -> list[str]:
    """Return task and verification lines whose claim is that CI passes."""
    lines = re.findall(r'^\s*- \[[ x]\] .*$', plan, re.M)
    lines += section(plan, 'Verification').splitlines()
    return [line for line in lines if _CI_PASSES.search(line)]


def unscoped_searches(plan: str) -> list[str]:
    """Return the ``## Verification`` searches that name none of the plan's files."""
    files = planned_files(plan)
    commands = re.findall(r'`([^`]+)`', section(plan, 'Verification'))
    return [
        command
        for command in commands
        if _SEARCH.search(command) and not any(path in command for path in files)
    ]


def claims_inside_only(plan: str) -> bool:
    """Whether the plan's spec says publish writes only inside the repository."""
    spec = section(plan, 'Spec changes')
    return re.search(r'only (inside|within)|never outside', spec, re.I) is not None


def names_limit(plan: str) -> bool:
    """Whether the plan's ``## Spec changes`` names something the mechanism does not stop."""
    return _LIMIT.search(section(plan, 'Spec changes')) is not None
