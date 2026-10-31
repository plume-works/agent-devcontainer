"""Set OpenCode's full-access permission policy in its user config."""

import json
import os
from pathlib import Path
import tempfile
from typing import Any

import json5

SCHEMA = 'https://opencode.ai/config.json'


def config_directory() -> Path:
    """Return OpenCode's config directory using its environment precedence."""
    configured = os.environ.get('OPENCODE_CONFIG_DIR')
    if configured:
        return Path(configured)
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
    if xdg_config_home:
        return Path(xdg_config_home) / 'opencode'
    return Path.home() / '.config/opencode'


def config_path(directory: Path) -> Path:
    """Return the highest-precedence user config file in ``directory``."""
    jsonc = directory / 'opencode.jsonc'
    return jsonc if jsonc.exists() else directory / 'opencode.json'


def load_config(path: Path) -> dict[str, Any]:
    """Load an OpenCode config, treating a missing or empty file as an object."""
    if not path.exists():
        return {}
    content = path.read_text(encoding='utf-8')
    if not content.strip():
        return {}
    loaded = json5.loads(content, allow_duplicate_keys=False)
    if not isinstance(loaded, dict):
        raise ValueError(f'{path} must contain a JSON object')
    return loaded


def apply_policy(current: dict[str, Any]) -> dict[str, Any]:
    """Return ``current`` with the managed OpenCode policy values set."""
    existing_permission = current.get('permission')
    permission = existing_permission if isinstance(existing_permission, dict) else {}
    existing_external = permission.get('external_directory')
    external = existing_external if isinstance(existing_external, dict) else {}

    unmanaged_permission = {
        key: value for key, value in permission.items() if key not in {'*', 'external_directory'}
    }
    unmanaged_external = {key: value for key, value in external.items() if key != '/**'}
    managed_permission = {
        '*': 'allow',
        **unmanaged_permission,
        'external_directory': {'/**': 'allow', **unmanaged_external},
    }

    # Keys keep their positions so an unchanged config rewrites byte-identically.
    updated = {} if '$schema' in current else {'$schema': SCHEMA}
    for key, value in current.items():
        updated[key] = {'$schema': SCHEMA, 'permission': managed_permission}.get(key, value)
    updated.setdefault('permission', managed_permission)
    return updated


def write_atomically(path: Path, content: str) -> None:
    """Replace ``path`` through a private temporary file beside it."""
    file_descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.')
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, 'w', encoding='utf-8') as temporary_file:
            temporary_file.write(content)
        temporary_path.chmod(0o600)
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def configure(directory: Path | None = None) -> None:
    """Set the managed policy in OpenCode's user config."""
    directory = directory or config_directory()
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    config = config_path(directory)
    updated = apply_policy(load_config(config))
    write_atomically(config, json.dumps(updated, indent=2, ensure_ascii=False) + '\n')
