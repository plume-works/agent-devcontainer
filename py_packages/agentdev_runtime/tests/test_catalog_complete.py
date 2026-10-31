"""Which catalog roots are complete enough to replace the staged catalog."""

from pathlib import Path

from agentdev_runtime import catalog


def write_root(root: Path, *, claude: bool = True, opencode: bool = True) -> Path:
    if claude:
        (root / catalog.CLAUDE_MANIFEST).parent.mkdir(parents=True)
        (root / catalog.CLAUDE_MANIFEST).write_text('{"name": "mock-market"}\n')
    if opencode:
        (root / catalog.OPENCODE_BRIDGE).mkdir(parents=True)
    return root


def test_a_root_without_a_codex_manifest_is_complete(tmp_path: Path) -> None:
    root = write_root(tmp_path)
    assert not (root / '.agents/plugins/marketplace.json').exists()
    assert catalog.complete(root)
    assert catalog.main(['complete', str(root)]) == 0


def test_a_root_without_the_claude_manifest_is_incomplete(tmp_path: Path) -> None:
    assert not catalog.complete(write_root(tmp_path, claude=False))


def test_a_root_without_the_opencode_bridge_is_incomplete(tmp_path: Path) -> None:
    assert not catalog.complete(write_root(tmp_path, opencode=False))
