#!/usr/bin/env python3
"""Configure Codex's persistent user settings inside the devcontainer."""

import argparse
import os
from pathlib import Path
import tempfile

import toml

# https://github.com/DeusData/codebase-memory-mcp#environment-variables
CMB_KNOWN_ENV_VARS = [
    'CBM_ALLOWED_ROOT',
    'CBM_CACHE_DIR',
    'CBM_DIAGNOSTICS',
    'CBM_DOWNLOAD_URL',
    'CBM_LOG_LEVEL',
    'CBM_WORKERS',
    'CBM_MEM_BUDGET_MB',
    'CBM_DUMP_VERIFY_MIN_RATIO',
]


def main(args: argparse.Namespace) -> None:
    """Patch codebase-memory-mcp codex configuration for custom environment."""
    codex_home = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
    config_path = codex_home / 'config.toml'

    codex_home.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(codex_home, 0o700)
    config = toml.load(config_path) if config_path.exists() else {}

    cbm_server = config.get('mcp_servers', {}).get('codebase-memory-mcp')
    if isinstance(cbm_server, dict):
        if args.revert:
            cbm_server.pop('env_vars', None)
        else:
            cbm_server['env_vars'] = CMB_KNOWN_ENV_VARS

    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=codex_home,
        prefix='config.toml.',
        delete=False,
    ) as config_file:
        toml.dump(config, config_file)
        temporary_path = Path(config_file.name)

    temporary_path.chmod(0o600)
    temporary_path.replace(config_path)


if __name__ == '__main__':
    argument_parser = argparse.ArgumentParser(
        description='Patch codebase-memory-mcp codex configuration for custom environment.'
    )
    argument_parser.add_argument(
        '--revert',
        action='store_true',
        help="Revert any previous patch to codex's config.toml",
    )
    args = argument_parser.parse_args()
    main(args)
