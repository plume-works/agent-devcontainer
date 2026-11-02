"""
Checks that every hub lists its members in sorted order.

A hub's inclusion links sort by member key with any `YYYYMMDD-` prefix removed,
so parallel pull requests that file members insert at different lines.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tomllib
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE = REPO_ROOT / 'docs' / 'knowledge'
IWE_CONFIG = REPO_ROOT / '.iwe' / 'config.toml'
TMP_ROOT = Path('/tmp/agentdev-tests')

FRONTMATTER = re.compile(r'\A---\n.*?\n---\n', re.S)
INCLUSION_LINK = re.compile(r'\A\[[^\]]*\]\(([^)\s]+)\)\Z', re.S)
DATE_PREFIX = re.compile(r'^\d{8}-')


def _hub_keys() -> list[str]:
    """Return the hub keys `[schemas.hub]` binds in `.iwe/config.toml`."""
    config = tomllib.loads(IWE_CONFIG.read_text())
    return list(config['schemas']['hub']['match'])


def member_links(body: str) -> list[str]:
    """Return the targets of the inclusion links in a hub body, in order."""
    body = FRONTMATTER.sub('', body)
    paragraphs = (p.strip() for p in re.split(r'\n\s*\n', body))
    return [m.group(1) for p in paragraphs if (m := INCLUSION_LINK.match(p))]


def sort_key(target: str) -> str:
    """Return a link target's member key without its directory or date prefix."""
    stem = target.rsplit('/', 1)[-1].removesuffix('.md')
    return DATE_PREFIX.sub('', stem)


def first_out_of_order(links: list[str]) -> str | None:
    """Return the first link that sorts before the link above it, if any."""
    for above, link in zip(links, links[1:], strict=False):
        if sort_key(link) < sort_key(above):
            return link
    return None


@pytest.mark.parametrize('hub', _hub_keys())
def test_hub_links_are_sorted(hub: str) -> None:
    """Every hub's inclusion links are sorted by member key."""
    links = member_links((KNOWLEDGE / f'{hub}.md').read_text())
    culprit = first_out_of_order(links)
    assert culprit is None, f'{hub}: {culprit} is out of order'


def test_out_of_order_link_is_named() -> None:
    """The check names the first link that breaks the order."""
    body = (
        '---\ntype: hub\n---\n# Plans\n\n'
        '[Beta](plans/20260101-beta.md)\n\n'
        '[Alpha, wrapped\nacross lines](plans/20261231-alpha.md)\n\n'
        '[Gamma](plans/20260601-gamma.md)\n'
    )
    assert member_links(body) == [
        'plans/20260101-beta.md',
        'plans/20261231-alpha.md',
        'plans/20260601-gamma.md',
    ]
    assert first_out_of_order(member_links(body)) == 'plans/20261231-alpha.md'


def test_date_prefix_is_ignored() -> None:
    """Plans sort by slug, not by the date they were filed."""
    links = ['plans/20261231-alpha.md', 'plans/20260101-beta.md']
    assert first_out_of_order(links) is None


def test_every_hub_is_bound() -> None:
    """The hub schema binds every document that declares `type: hub`."""
    hubs = sorted(
        str(p.relative_to(KNOWLEDGE).with_suffix(''))
        for p in (KNOWLEDGE / 'data').glob('*.md')
        if re.search(r'^type: hub$', p.read_text(), re.M)
    )
    assert hubs == sorted(_hub_keys())


@pytest.mark.skipif(shutil.which('iwe') is None, reason='the iwe CLI is not installed')
def test_sectioned_hub_is_rejected() -> None:
    """A `##` section in a hub body fails validation and names the hub."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'hub-order-{uuid4().hex}'
    try:
        (root / 'docs' / 'knowledge').mkdir(parents=True)
        shutil.copytree(IWE_CONFIG.parent, root / '.iwe')
        shutil.copytree(KNOWLEDGE / 'data', root / 'docs' / 'knowledge' / 'data')
        hub = root / 'docs' / 'knowledge' / 'data' / 'concept.md'
        hub.write_text(hub.read_text() + '\n## Done\n')
        result = subprocess.run(
            ['iwe', 'schema', 'validate'],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)
    assert result.returncode != 0
    assert 'data/concept' in result.stdout
