"""How a catalog root registers its OpenCode bridge in the user's opencode.json."""

import json
from pathlib import Path

from agentdev_runtime import catalog
from agentdev_runtime.settings import Settings


def test_registering_a_root_replaces_every_earlier_bridge_entry(tmp_path: Path) -> None:
    root = tmp_path / 'catalog'
    (root / catalog.OPENCODE_BRIDGE).mkdir(parents=True)
    config_dir = tmp_path / 'opencode'
    config_dir.mkdir()
    (config_dir / 'opencode.json').write_text(
        json.dumps(
            {
                'plugin': [
                    'other',
                    f'/elsewhere/{catalog.OPENCODE_BRIDGE}',
                    f'/opt/agentdev/{catalog.REPLACED_BRIDGE}',
                ],
                'theme': 'x',
            }
        )
    )

    catalog.opencode(Settings({'OPENCODE_CONFIG_DIR': str(config_dir)}), str(root))

    assert json.loads((config_dir / 'opencode.json').read_text()) == {
        'plugin': ['other', str(root / catalog.OPENCODE_BRIDGE)],
        'theme': 'x',
    }
