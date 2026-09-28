import json
import os
from pathlib import Path
import stat
import subprocess

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / ".devcontainer/scripts/seed-agent-auth.sh"
COMPOSE = REPO_ROOT / ".devcontainer/docker-compose.yml"


def run_seeder(tmp_path: Path, *, claude: str = "", codex: str = ""):
    claude_path = tmp_path / "claude" / ".credentials.json"
    codex_path = tmp_path / "codex" / "auth.json"
    env = os.environ | {
        "AGENTDEV_CLAUDE_JSON": claude,
        "AGENTDEV_CODEX_JSON": codex,
        "AGENTDEV_CLAUDE_AUTH_PATH": str(claude_path),
        "AGENTDEV_CODEX_AUTH_PATH": str(codex_path),
    }
    result = subprocess.run([SCRIPT], env=env, text=True, capture_output=True)
    return result, claude_path, codex_path


def test_seeds_both_credentials_with_private_permissions(tmp_path):
    claude = json.dumps({"claudeAiOauth": {"accessToken": "claude-secret"}})
    codex = json.dumps({"auth_mode": "chatgpt", "tokens": {"refresh_token": "codex-secret"}})

    result, claude_path, codex_path = run_seeder(tmp_path, claude=claude, codex=codex)

    assert result.returncode == 0, result.stderr
    assert json.loads(claude_path.read_text()) == json.loads(claude)
    assert json.loads(codex_path.read_text()) == json.loads(codex)
    assert stat.S_IMODE(claude_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(codex_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(claude_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(codex_path.stat().st_mode) == 0o600
    assert "claude-secret" not in result.stdout + result.stderr
    assert "codex-secret" not in result.stdout + result.stderr


def test_preserves_existing_nonempty_credentials(tmp_path):
    claude_path = tmp_path / "claude" / ".credentials.json"
    codex_path = tmp_path / "codex" / "auth.json"
    for path in (claude_path, codex_path):
        path.parent.mkdir(parents=True)
        path.write_text('{"existing": true}')
        path.chmod(0o644)

    result, _, _ = run_seeder(
        tmp_path,
        claude='{"replacement": "claude-secret"}',
        codex='{"replacement": "codex-secret"}',
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(claude_path.read_text()) == {"existing": True}
    assert json.loads(codex_path.read_text()) == {"existing": True}
    assert stat.S_IMODE(claude_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(codex_path.stat().st_mode) == 0o600


def test_rejects_invalid_json_without_creating_credential(tmp_path):
    result, claude_path, _ = run_seeder(tmp_path, claude="not-json")

    assert result.returncode != 0
    assert not claude_path.exists()
    assert "not-json" not in result.stdout + result.stderr


def test_skips_unset_credentials(tmp_path):
    result, claude_path, codex_path = run_seeder(tmp_path)

    assert result.returncode == 0, result.stderr
    assert not claude_path.exists()
    assert not codex_path.exists()


def test_compose_passes_auth_seed_environment():
    compose = COMPOSE.read_text()

    assert "AGENTDEV_CLAUDE_JSON: ${AGENTDEV_CLAUDE_JSON:-}" in compose
    assert "AGENTDEV_CODEX_JSON: ${AGENTDEV_CODEX_JSON:-}" in compose
