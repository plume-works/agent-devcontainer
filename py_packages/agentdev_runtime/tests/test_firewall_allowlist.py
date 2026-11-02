"""The firewall's allowlist: where it is read from, what it accepts, and GitHub's ranges."""

from pathlib import Path

from agentdev_runtime import firewall
from agentdev_runtime.settings import DEPLOY, DEVCONTAINER, Settings
import pytest


def test_entries_drop_comments_blanks_and_whitespace() -> None:
    text = 'github-meta  # GitHub\n\n  # only a comment\nexample .org\n'
    assert firewall.entries(text) == [(1, 'github-meta'), (4, 'example.org')]


@pytest.mark.parametrize('entry', ['github-meta', 'registry-1.docker.io', '*.example-cdn.net'])
def test_valid_entries_pass(tmp_path: Path, entry: str) -> None:
    path = tmp_path / 'allowlist.txt'
    path.write_text(entry + '\n')
    assert firewall.validate_allowlist(path) == [entry]


@pytest.mark.parametrize('entry', ['https://evil.example/path', 'localhost', '-bad.example'])
def test_invalid_entries_name_their_line(tmp_path: Path, entry: str) -> None:
    path = tmp_path / 'allowlist.txt'
    path.write_text(f'github-meta\n{entry}\n')
    with pytest.raises(firewall.FirewallError, match=f'{path}:2:'):
        firewall.validate_allowlist(path)


def test_github_ranges_collapse_ipv4_and_drop_ipv6() -> None:
    meta = {
        'web': ['140.82.112.0/20', '2a0a:a440::/29'],
        'api': ['140.82.112.0/21', '140.82.128.0/20'],
        'git': ['192.30.252.0/22'],
    }
    assert firewall.github_ranges(meta) == [
        '140.82.112.0/20',
        '140.82.128.0/20',
        '192.30.252.0/22',
    ]


@pytest.mark.parametrize('meta', [{}, {'web': [], 'api': ['1.0.0.0/8'], 'git': ['1.0.0.0/8']}, []])
def test_github_meta_missing_fields_fails(meta: object) -> None:
    with pytest.raises(firewall.FirewallError, match='missing required fields'):
        firewall.github_ranges(meta)


def test_proxy_cidrs_accept_commas_and_spaces() -> None:
    assert firewall.proxy_cidrs('10.0.0.1/32, 10.1.0.0/16', '4096') == [
        '10.0.0.1/32',
        '10.1.0.0/16',
    ]


def test_a_devcontainer_reads_the_checkout_allowlist_when_present(tmp_path: Path) -> None:
    checkout = tmp_path / '.devcontainer/firewall-allowlist.txt'
    settings = Settings(
        {'AGENTDEV_RUNTIME_MODE': DEVCONTAINER, 'DEV_WORKSPACE_FOLDER': str(tmp_path)}
    )
    assert firewall.allowlist_path(settings) == firewall.IMAGE_ALLOWLIST
    checkout.parent.mkdir()
    checkout.write_text('github-meta\n')
    assert firewall.allowlist_path(settings) == checkout


def test_deploy_reads_the_image_copy_or_the_setting(tmp_path: Path) -> None:
    (tmp_path / '.devcontainer').mkdir()
    (tmp_path / '.devcontainer/firewall-allowlist.txt').write_text('github-meta\n')
    deploy = {'AGENTDEV_RUNTIME_MODE': DEPLOY, 'DEV_WORKSPACE_FOLDER': str(tmp_path)}
    assert firewall.allowlist_path(Settings(deploy)) == firewall.IMAGE_ALLOWLIST
    explicit = Settings({**deploy, 'FIREWALL_ALLOWLIST': '/x/allow.txt'})
    assert firewall.allowlist_path(explicit) == Path('/x/allow.txt')


def test_a_set_allowlist_wins_over_the_checkout_copy_in_a_devcontainer(tmp_path: Path) -> None:
    (tmp_path / '.devcontainer').mkdir()
    (tmp_path / '.devcontainer/firewall-allowlist.txt').write_text('github-meta\n')
    settings = Settings(
        {
            'AGENTDEV_RUNTIME_MODE': DEVCONTAINER,
            'DEV_WORKSPACE_FOLDER': str(tmp_path),
            'FIREWALL_ALLOWLIST': '/x/allow.txt',
        }
    )
    assert firewall.allowlist_path(settings) == Path('/x/allow.txt')
