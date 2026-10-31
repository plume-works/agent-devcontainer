"""
Pre-answer Claude's first-run prompts: onboarding, Remote Control, trust, and project MCP.

Spec: claude-remote-control.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import tempfile

from agentdev_runtime import settings as env


def update_json(path: Path, mutate: Callable[[dict], None]) -> None:
    """Rewrite a JSON object in place; a symlink into a persistent volume stays a symlink."""
    path = Path(os.path.realpath(path))
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        data = {}
    mutate(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp = tempfile.mkstemp(dir=path.parent, prefix='.preapprove.')
    with os.fdopen(descriptor, 'w') as target:
        json.dump(data, target, indent=2)
        target.write('\n')
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def preapprove(settings: env.Settings) -> None:
    if settings.raw('AGENTDEV_SKIP_CLAUDE_PREAPPROVE'):
        print('AGENTDEV_SKIP_CLAUDE_PREAPPROVE is set; skipping Claude workspace pre-approval.')
        return
    workspace = settings.get('DEV_WORKSPACE_FOLDER')

    def approve_state(state: dict) -> None:
        state['hasCompletedOnboarding'] = True
        state['remoteDialogSeen'] = True
        project = state.setdefault('projects', {}).setdefault(workspace, {})
        project['hasTrustDialogAccepted'] = True

    def approve_mcp(project_settings: dict) -> None:
        # Keeps disabledMcpjsonServers; see spec/claude-remote-control.
        project_settings['enableAllProjectMcpServers'] = True

    update_json(settings.path('AGENTDEV_CLAUDE_STATE_PATH'), approve_state)
    update_json(Path(workspace) / '.claude/settings.local.json', approve_mcp)
    print(f'Pre-approved Claude onboarding, Remote Control, trust, and MCP for {workspace}.')
