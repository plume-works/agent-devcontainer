"""Contract tests for the Playwright browser bundled in agentdev-base."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYBOOK_PATH = REPO_ROOT / 'ansible/playbooks/setup-dev.yml'
GROUP_VARS = yaml.safe_load((REPO_ROOT / 'ansible/playbooks/group_vars/all.yml').read_text())
ROLE_ROOT = REPO_ROOT / 'ansible/roles/playwright_browser'
DEFAULTS = (ROLE_ROOT / 'defaults/main.yml').read_text()
DEFAULT_VALUES = yaml.safe_load(DEFAULTS)
TASKS = (ROLE_ROOT / 'tasks/main.yml').read_text()
DOCKERFILE = (REPO_ROOT / 'docker/base/agentdev-base.Dockerfile').read_text()
CI = yaml.safe_load((REPO_ROOT / '.github/workflows/ci.yml').read_text())


def role_name(role: str | dict) -> str:
    """Return the role name from either supported playbook role shape."""
    return role if isinstance(role, str) else role['role']


def test_playwright_role_is_opt_in_after_bun_and_node() -> None:
    playbook = yaml.safe_load(PLAYBOOK_PATH.read_text())
    roles = playbook[0]['roles']
    names = [role_name(role) for role in roles]
    playwright = roles[names.index('playwright_browser')]

    assert names.index('bun_setup') < names.index('nodejs') < names.index('playwright_browser')
    assert playwright['when'] == 'install_playwright_browser | default(false) | bool'
    assert 'playwright_browser' in playwright['tags']
    assert GROUP_VARS['install_playwright_browser'] is False


def test_role_pins_the_cli_and_matching_chromium_in_an_image_owned_path() -> None:
    assert '# renovate: datasource=npm depName=playwright' in DEFAULTS
    assert 'playwright_browser_path: /opt/playwright' in DEFAULTS
    assert 'playwright_browser_package: playwright' in DEFAULTS
    assert "'--global'" not in TASKS
    assert '      - --global' in TASKS
    assert '      - --exact' in TASKS
    assert "map('regex_replace', '^[^@A-Za-z]+', '')" in TASKS
    assert 'not in playwright_browser_bun_global_specs' in TASKS
    assert '      - --with-deps' in TASKS
    assert '      - chromium' in TASKS
    assert 'PLAYWRIGHT_BROWSERS_PATH: "{{ playwright_browser_path }}"' in TASKS
    assert (
        "playwright_browser_cli_version.stdout != 'Version ' ~ playwright_browser_version" in TASKS
    )
    assert "or 'chromium-' not in playwright_browser_list.stdout" in TASKS
    assert 'mode: a+rwX' in TASKS
    assert 'recurse: true' in TASKS


def test_desktop_image_enables_and_describes_the_pinned_browser() -> None:
    version = DEFAULT_VALUES['playwright_browser_version']

    assert 'ARG PLAYWRIGHT_VERSION\n' in DOCKERFILE
    assert f'ARG PLAYWRIGHT_VERSION={version}' not in DOCKERFILE
    assert 'test -n "$PLAYWRIGHT_VERSION"' in DOCKERFILE
    assert 'install_playwright_browser=true' in DOCKERFILE
    assert 'playwright_browser_version=$PLAYWRIGHT_VERSION' in DOCKERFILE
    assert 'ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright' in DOCKERFILE
    assert 'org.opencontainers.image.version.playwright="$PLAYWRIGHT_VERSION"' in DOCKERFILE


def test_image_build_derives_the_playwright_version_from_the_role_default() -> None:
    build_steps = CI['jobs']['build-dev-image']['steps']
    version_step = next(step for step in build_steps if step.get('id') == 'playwright_version')
    base_build = next(
        step for step in build_steps if step.get('name') == 'Build agentdev base image'
    )

    assert 'ansible/roles/playwright_browser/defaults/main.yml' in version_step['run']
    assert 'playwright_browser_version:' in version_step['run']
    assert (
        'PLAYWRIGHT_VERSION=${{ steps.playwright_version.outputs.version }}'
        in (base_build['with']['build-args'])
    )


def test_native_image_acceptance_launches_bundled_chromium() -> None:
    command = CI['jobs']['dev-container-ci']['steps'][-2]['with']['runCmd']

    assert 'playwright --version' in command
    assert 'mkdir -p .tmp' in command
    assert 'playwright screenshot --browser chromium' in command
    assert "'data:text/html,<title>playwright-smoke</title>'" in command
    assert 'test -s .tmp/playwright-smoke.png' in command
