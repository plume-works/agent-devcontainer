#!/usr/bin/env python3
"""Download AI Responder runs and their claude-responder-output artifacts for a UTC range."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

USAGE = """\
Usage: scripts/download-claude-responder-runs.py --start DATETIME --end DATETIME [options]

Downloads AI Responder runs and claude-responder-output artifacts for a UTC
datetime range. DATETIME values are parsed with GNU date and normalized to UTC.

Options:
  --start DATETIME       Inclusive range start, for example 2026-09-01T00:00:00Z.
  --end DATETIME         Inclusive range end, for example 2026-09-04T04:35:05Z.
  --repo OWNER/REPO      GitHub repository. Defaults to the current gh repo.
  --workflow NAME        Workflow file name or numeric id. Default: ai-responder.yml.
  --artifact-name NAME   Artifact to download. Default: claude-responder-output.
  --output DIR           Output directory. Default: ./.tmp/claude-review-costs.
  --limit N              Max matching runs to keep after API filtering. Default: 1000.
  -h, --help             Show this help.

Outputs:
  runs.json
  all-ai-responder-runs.csv
  artifacts/<run_id>.json
  claude-output-artifacts.json
  downloads/<run_id>/claude-execution-output.json"""
RUN_FIELDS = """
    .workflow_runs[]
    | {
        databaseId: .id,
        displayTitle: .display_title,
        event,
        headBranch: .head_branch,
        headSha: .head_sha,
        conclusion: (.conclusion // ""),
        status,
        createdAt: .created_at,
        updatedAt: .updated_at,
        startedAt: .run_started_at,
        url: .html_url,
        workflowName: .name,
        attempt: .run_attempt
      }
"""
CSV_HEADER = [
    'run_id',
    'created_at',
    'event',
    'conclusion',
    'status',
    'head_branch',
    'title',
    'url',
]


class Usage(Exception):
    """A usage error; exits 2."""


def fail(message: str, code: int) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def parse(argv: list[str]) -> argparse.Namespace:
    values = {
        'start': '',
        'end': '',
        'repo': '',
        'workflow': 'ai-responder.yml',
        'artifact_name': 'claude-responder-output',
        'output': './.tmp/claude-review-costs',
        'limit': '1000',
    }
    flags = {f'--{name.replace("_", "-")}': name for name in values}
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in ('-h', '--help'):
            print(USAGE)
            raise SystemExit(0)
        if argument not in flags:
            print(f'Unknown argument: {argument}', file=sys.stderr)
            print(USAGE, file=sys.stderr)
            raise SystemExit(2)
        if index + 1 >= len(argv):
            fail(f'{argument} requires a value.', 2)
        values[flags[argument]] = argv[index + 1]
        index += 2
    if not values['start'] or not values['end']:
        print('--start and --end are required.', file=sys.stderr)
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)
    limit = values['limit']
    if not (limit.isdigit() and limit[0] != '0'):
        fail(f'--limit must be a positive integer: {limit}', 2)
    return argparse.Namespace(**values)


def normalize_datetime(value: str) -> str:
    result = subprocess.run(
        ['date', '-u', '-d', value, '+%Y-%m-%dT%H:%M:%SZ'], capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        fail(f'Could not parse datetime: {value}', 2)
    return result.stdout.strip()


def gh(*args: str) -> str:
    return subprocess.run(['gh', *args], check=True, capture_output=True, text=True).stdout


def csv_field(value: object) -> str:
    """Render one field as jq's @csv does: strings quoted, numbers bare, null empty."""
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return json.dumps(value)
    return '"' + str(value).replace('"', '""') + '"'


def write_json(path: Path, document: object) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n')


def main(argv: list[str]) -> int:
    args = parse(argv)
    for command in ('gh', 'date'):
        if shutil.which(command) is None:
            fail(f'{command} is required.', 1)
    subprocess.run(['gh', 'auth', 'status'], check=True, stdout=subprocess.DEVNULL)
    repo = (
        args.repo
        or gh('repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner').strip()
    )
    start, end = normalize_datetime(args.start), normalize_datetime(args.end)
    if start > end:
        fail(f'Start must be earlier than or equal to end: {start} > {end}', 2)
    output = Path(args.output)
    (output / 'artifacts').mkdir(parents=True, exist_ok=True)
    (output / 'downloads').mkdir(parents=True, exist_ok=True)

    print(f'Listing {args.workflow} runs in {repo} from {start} through {end}.', file=sys.stderr)
    raw = gh(
        'api',
        '--paginate',
        '--method',
        'GET',
        f'repos/{repo}/actions/workflows/{args.workflow}/runs',
        '-f',
        f'created={start}..{end}',
        '-f',
        'per_page=100',
        '--jq',
        RUN_FIELDS,
    )
    (output / 'runs.raw.json').write_text(raw)
    runs = [json.loads(line) for line in raw.splitlines() if line.strip()]
    runs = list(reversed(sorted(runs, key=lambda run: run['createdAt'])))[: int(args.limit)]
    write_json(output / 'runs.json', runs)

    rows = [CSV_HEADER] + [
        [
            run['databaseId'],
            run['createdAt'],
            run['event'],
            run.get('conclusion') or '',
            run['status'],
            run.get('headBranch') or '',
            run['displayTitle'],
            run['url'],
        ]
        for run in runs
    ]
    (output / 'all-ai-responder-runs.csv').write_text(
        ''.join(','.join(csv_field(field) for field in row) + '\n' for row in rows)
    )

    for run in runs:
        artifact_json = output / 'artifacts' / f'{run["databaseId"]}.json'
        if not artifact_json.is_file() or artifact_json.stat().st_size == 0:
            print(f'Fetching artifacts for run {run["databaseId"]}.', file=sys.stderr)
            artifact_json.write_text(
                gh('api', f'repos/{repo}/actions/runs/{run["databaseId"]}/artifacts')
            )

    # Only this run's listing counts: a reused output directory keeps older runs' files.
    selected = []
    for run in runs:
        listing = json.loads((output / 'artifacts' / f'{run["databaseId"]}.json').read_text())
        for artifact in listing.get('artifacts') or []:
            if artifact.get('name') != args.artifact_name:
                continue
            selected.append(
                {
                    'run_id': artifact['workflow_run']['id'],
                    'artifact_id': artifact['id'],
                    'name': artifact['name'],
                    'expired': artifact['expired'],
                    'created_at': artifact['created_at'],
                    'expires_at': artifact['expires_at'],
                    'size_in_bytes': artifact['size_in_bytes'],
                }
            )
    summary = {
        'artifact_name': args.artifact_name,
        'count': len(selected),
        'expired': sum(1 for artifact in selected if artifact['expired']),
        'unexpired': sum(1 for artifact in selected if not artifact['expired']),
        'artifacts': selected,
    }
    write_json(output / 'claude-output-artifacts.json', summary)

    for artifact in selected:
        if artifact['expired']:
            continue
        destination = output / 'downloads' / str(artifact['run_id'])
        marker = destination / '.downloaded'
        destination.mkdir(parents=True, exist_ok=True)
        if not marker.exists():
            print(
                f'Downloading {args.artifact_name} for run {artifact["run_id"]}.', file=sys.stderr
            )
            subprocess.run(
                [
                    'gh',
                    'run',
                    'download',
                    str(artifact['run_id']),
                    '--repo',
                    repo,
                    '--name',
                    args.artifact_name,
                    '--dir',
                    str(destination),
                ],
                check=True,
            )
            marker.touch()

    print(
        json.dumps(
            {
                'repo': repo,
                'workflow': args.workflow,
                'start_utc': start,
                'end_utc': end,
                'runs': len(runs),
                'artifacts': summary['unexpired'],
            },
            indent=2,
        )
    )
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode or 1)
