"""Regression tests for claude responder run artifact downloads."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import textwrap


def test_download_aggregates_only_current_run_artifacts(tmp_path: Path) -> None:
    """A reused output directory must not aggregate stale artifact cache entries."""
    repo_root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / 'output'
    artifacts_dir = output_dir / 'artifacts'
    artifacts_dir.mkdir(parents=True)
    stale_run_id = 111
    current_run_id = 222

    (artifacts_dir / f'{stale_run_id}.json').write_text(
        json.dumps(
            {
                'artifacts': [
                    {
                        'id': 9001,
                        'name': 'claude-responder-output',
                        'expired': False,
                        'created_at': '2026-09-01T00:00:00Z',
                        'expires_at': '2026-12-01T00:00:00Z',
                        'size_in_bytes': 123,
                        'workflow_run': {'id': stale_run_id},
                    }
                ]
            }
        ),
        encoding='utf-8',
    )

    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    gh_stub = bin_dir / 'gh'
    gh_stub.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail

            if [[ "${{1:-}}" == "auth" && "${{2:-}}" == "status" ]]; then
              exit 0
            fi

            if [[ "${{1:-}}" == "api" && "$*" == *"/actions/workflows/"*"/runs"* ]]; then
              printf '%s\\n' '{{"databaseId":{current_run_id},"displayTitle":"Current run","event":"pull_request","headBranch":"iwe-map-skill","headSha":"abc123","conclusion":"success","status":"completed","createdAt":"2026-09-03T00:00:00Z","updatedAt":"2026-09-03T00:01:00Z","startedAt":"2026-09-03T00:00:10Z","url":"https://example.test/runs/{current_run_id}","workflowName":"AI Responder","attempt":1}}'
              exit 0
            fi

            if [[ "${{1:-}}" == "api" && "$*" == *"/actions/runs/{current_run_id}/artifacts"* ]]; then
              cat <<'JSON'
            {{"artifacts":[{{"id":9002,"name":"claude-responder-output","expired":false,"created_at":"2026-09-03T00:00:00Z","expires_at":"2026-12-03T00:00:00Z","size_in_bytes":456,"workflow_run":{{"id":{current_run_id}}}}}]}}
            JSON
              exit 0
            fi

            if [[ "${{1:-}}" == "run" && "${{2:-}}" == "download" ]]; then
              exit 0
            fi

            printf 'unexpected gh invocation: %s\\n' "$*" >&2
            exit 1
            """
        ),
        encoding='utf-8',
    )
    gh_stub.chmod(0o755)

    env = os.environ.copy()
    env['PATH'] = f'{bin_dir}{os.pathsep}{env["PATH"]}'

    subprocess.run(
        [
            str(repo_root / 'scripts/download-claude-responder-runs.sh'),
            '--start',
            '2026-09-03T00:00:00Z',
            '--end',
            '2026-09-03T23:59:59Z',
            '--repo',
            'plume-works/agent-devcontainer',
            '--output',
            str(output_dir),
        ],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    aggregate = json.loads((output_dir / 'claude-output-artifacts.json').read_text())
    run_ids = [artifact['run_id'] for artifact in aggregate['artifacts']]

    assert run_ids == [current_run_id]
    assert aggregate['count'] == 1
    assert aggregate['unexpired'] == 1
    assert not (output_dir / 'downloads' / str(stale_run_id) / '.downloaded').exists()
