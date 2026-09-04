#!/usr/bin/env python3
"""Summarize Claude responder token and cost artifacts."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
from typing import Any

TOKEN_FIELDS = (
    'input_tokens',
    'cache_creation_input_tokens',
    'cache_read_input_tokens',
    'output_tokens',
)


def parse_args() -> argparse.Namespace:
    """Parse command-line options for the cost analyzer."""
    parser = argparse.ArgumentParser(
        description=('Analyze artifacts downloaded by scripts/download-claude-responder-runs.sh.')
    )
    parser.add_argument(
        '--data-dir',
        default='./.tmp/claude-review-costs',
        help='Directory containing runs.json, claude-output-artifacts.json, and downloads/.',
    )
    parser.add_argument(
        '--output-dir',
        help='Directory for generated CSV/JSON summaries. Defaults to --data-dir.',
    )
    return parser.parse_args()


def add_usage(target: dict[str, float], usage: dict[str, Any]) -> None:
    """Add token usage fields into an aggregate usage dictionary."""
    for field in TOKEN_FIELDS:
        target[field] += float(usage.get(field) or 0)
    details = usage.get('output_tokens_details') or {}
    target['thinking_tokens'] += float(details.get('thinking_tokens') or 0)


def model_usage_row(usage: dict[str, Any]) -> list[float]:
    """Return the token fields used for per-model cost fitting."""
    return [
        float(usage.get('inputTokens') or 0),
        float(usage.get('cacheCreationInputTokens') or 0),
        float(usage.get('cacheReadInputTokens') or 0),
        float(usage.get('outputTokens') or 0),
    ]


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    """Solve a square linear system with Gaussian elimination."""
    size = len(vector)
    augmented = [row[:] + [value] for row, value in zip(matrix, vector, strict=True)]

    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            return None
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_value = augmented[col][col]
        for item in range(col, size + 1):
            augmented[col][item] /= pivot_value
        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            for item in range(col, size + 1):
                augmented[row][item] -= factor * augmented[col][item]

    return [augmented[row][size] for row in range(size)]


def least_squares(rows: list[list[float]], costs: list[float]) -> list[float] | None:
    """Fit usage-to-cost coefficients by ordinary least squares."""
    width = len(rows[0])
    normal = [[0.0 for _ in range(width)] for _ in range(width)]
    rhs = [0.0 for _ in range(width)]
    for row, cost in zip(rows, costs, strict=True):
        for left in range(width):
            rhs[left] += row[left] * cost
            for right in range(width):
                normal[left][right] += row[left] * row[right]
    return solve_linear_system(normal, rhs)


def cost_from_usage(usage: dict[str, float], coeffs: list[float] | None) -> float:
    """Estimate cost from token usage and fitted coefficients."""
    if coeffs is None:
        return 0.0
    return sum(coeff * usage[field] for coeff, field in zip(coeffs, TOKEN_FIELDS, strict=True))


def read_json(path: Path) -> Any:
    """Read a JSON document from disk."""
    return json.loads(path.read_text())


def result_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the final result event from a Claude execution log."""
    result_events = [event for event in events if event.get('type') == 'result']
    return result_events[-1] if result_events else {}


def assistant_usage_by_message(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index assistant events that carry message usage by stable message key."""
    messages: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get('type') != 'assistant':
            continue
        message = event.get('message') or {}
        if not message.get('usage'):
            continue
        key = message.get('id') or event.get('request_id') or event.get('uuid')
        messages[str(key)] = event
    return messages


def task_rows(
    run_id: int,
    metadata: dict[str, Any],
    events: list[dict[str, Any]],
    coefficients: dict[str, list[float] | None],
    run_cost_usd: float,
) -> list[dict[str, Any]]:
    """Build one cost row for each observed subagent task and model."""
    tasks = {
        event.get('task_id'): {
            'description': event.get('description') or 'unknown',
            'subagent_type': event.get('subagent_type') or 'unknown',
        }
        for event in events
        if event.get('type') == 'system' and event.get('subtype') == 'task_started'
    }
    task_progress: dict[str, dict[str, int]] = defaultdict(
        lambda: {'reported_total_tokens': 0, 'tool_uses': 0, 'duration_ms': 0}
    )
    for event in events:
        if event.get('type') != 'system' or not str(event.get('subtype', '')).startswith('task_'):
            continue
        task_id = event.get('task_id')
        usage = event.get('usage') or {}
        if task_id not in tasks or not usage:
            continue
        progress = task_progress[str(task_id)]
        progress['reported_total_tokens'] = max(
            progress['reported_total_tokens'], int(usage.get('total_tokens') or 0)
        )
        progress['tool_uses'] = max(progress['tool_uses'], int(usage.get('tool_uses') or 0))
        progress['duration_ms'] = max(progress['duration_ms'], int(usage.get('duration_ms') or 0))

    assistant_usage: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    message_counts: dict[tuple[str, str, str], int] = defaultdict(int)
    models_by_description: dict[str, set[str]] = defaultdict(set)
    for event in assistant_usage_by_message(events).values():
        if not event.get('subagent_type'):
            continue
        message = event.get('message') or {}
        usage = message.get('usage') or {}
        model = message.get('model') or 'unknown'
        description = event.get('task_description') or 'unknown'
        key = (description, event.get('subagent_type') or 'unknown', model)
        add_usage(assistant_usage[key], usage)
        message_counts[key] += 1
        models_by_description[description].add(model)

    rows = []
    for task_id, task in sorted(tasks.items(), key=lambda item: item[1]['description']):
        description = task['description']
        models = sorted(models_by_description.get(description) or {'unknown'})
        for model in models:
            key = (description, task['subagent_type'], model)
            usage = assistant_usage.get(key, defaultdict(float))
            rows.append(
                {
                    'run_id': run_id,
                    'created_at': metadata.get('createdAt', ''),
                    'title': metadata.get('displayTitle', ''),
                    'event': metadata.get('event', ''),
                    'conclusion': metadata.get('conclusion', ''),
                    'task_id': task_id,
                    'subagent_description': description,
                    'subagent_type': task['subagent_type'],
                    'model': model,
                    'reported_total_tokens': task_progress[str(task_id)]['reported_total_tokens'],
                    'tool_uses': task_progress[str(task_id)]['tool_uses'],
                    'duration_ms': task_progress[str(task_id)]['duration_ms'],
                    'assistant_messages': message_counts[key],
                    'assistant_input_tokens': int(usage['input_tokens']),
                    'assistant_cache_creation_input_tokens': int(
                        usage['cache_creation_input_tokens']
                    ),
                    'assistant_cache_read_input_tokens': int(usage['cache_read_input_tokens']),
                    'assistant_output_tokens_observed': int(usage['output_tokens']),
                    'assistant_thinking_tokens_observed': int(usage['thinking_tokens']),
                    'estimated_cost_usd': cost_from_usage(usage, coefficients.get(model)),
                    'allocated_run_cost_usd': 0.0,
                }
            )
    total_reported_tokens = sum(row['reported_total_tokens'] for row in rows)
    if total_reported_tokens:
        for row in rows:
            row['allocated_run_cost_usd'] = (
                run_cost_usd * row['reported_total_tokens'] / total_reported_tokens
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write dictionaries as a CSV file, preserving row key order."""
    if not rows:
        path.write_text('')
        return
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Read downloaded responder artifacts and write cost summaries."""
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir) if args.output_dir else data_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    runs_path = data_dir / 'runs.json'
    if not runs_path.exists():
        runs_path = data_dir / 'runs-sep1-plus.json'
    runs = {item['databaseId']: item for item in read_json(runs_path)}
    artifacts = read_json(data_dir / 'claude-output-artifacts.json')['artifacts']
    artifact_run_ids = {item['run_id'] for item in artifacts if not item['expired']}

    usage_rows_by_model: dict[str, list[list[float]]] = defaultdict(list)
    costs_by_model: dict[str, list[float]] = defaultdict(list)
    parsed_runs = []
    for run_id in sorted(artifact_run_ids):
        path = data_dir / 'downloads' / str(run_id) / 'claude-execution-output.json'
        if not path.exists():
            continue
        events = read_json(path)
        result = result_event(events)
        for model, usage in (result.get('modelUsage') or {}).items():
            usage_rows_by_model[model].append(model_usage_row(usage))
            costs_by_model[model].append(float(usage.get('costUSD') or 0))
        parsed_runs.append((run_id, events, result))

    coefficients = {
        model: least_squares(rows, costs_by_model[model])
        for model, rows in usage_rows_by_model.items()
        if rows
    }

    run_rows = []
    subagent_rows = []
    model_rows = []
    for run_id, events, result in parsed_runs:
        metadata = runs.get(run_id, {})
        exact_cost = float(result.get('total_cost_usd') or 0)
        run_usage = defaultdict(float)
        add_usage(run_usage, result.get('usage') or {})

        model_cost = 0.0
        for model, usage in (result.get('modelUsage') or {}).items():
            cost = float(usage.get('costUSD') or 0)
            model_cost += cost
            model_rows.append(
                {
                    'run_id': run_id,
                    'created_at': metadata.get('createdAt', ''),
                    'title': metadata.get('displayTitle', ''),
                    'model': model,
                    'input_tokens': usage.get('inputTokens') or 0,
                    'cache_creation_input_tokens': usage.get('cacheCreationInputTokens') or 0,
                    'cache_read_input_tokens': usage.get('cacheReadInputTokens') or 0,
                    'output_tokens': usage.get('outputTokens') or 0,
                    'thinking_tokens': usage.get('thinkingTokens') or 0,
                    'cost_usd': cost,
                }
            )

        stats = result.get('subagent_stats') or {}
        run_rows.append(
            {
                'run_id': run_id,
                'created_at': metadata.get('createdAt', ''),
                'title': metadata.get('displayTitle', ''),
                'event': metadata.get('event', ''),
                'conclusion': metadata.get('conclusion', ''),
                'url': metadata.get('url', ''),
                'total_cost_usd': exact_cost,
                'model_cost_usd': model_cost,
                'subagents_spawned': stats.get('spawned', 0),
                'subagents_completed': stats.get('completed', 0),
                'subagents_failed': stats.get('failed', 0),
                'input_tokens': int(run_usage['input_tokens']),
                'cache_creation_input_tokens': int(run_usage['cache_creation_input_tokens']),
                'cache_read_input_tokens': int(run_usage['cache_read_input_tokens']),
                'output_tokens': int(run_usage['output_tokens']),
                'thinking_tokens': int(run_usage['thinking_tokens']),
            }
        )
        subagent_rows.extend(task_rows(run_id, metadata, events, coefficients, exact_cost))

    created_values = [item.get('createdAt', '') for item in runs.values() if item.get('createdAt')]
    conclusion_values = {item.get('conclusion') or 'in_progress' for item in runs.values()}
    conclusion_counts = {
        conclusion: sum(
            1 for item in runs.values() if (item.get('conclusion') or 'in_progress') == conclusion
        )
        for conclusion in conclusion_values
    }
    summary = {
        'window_start_utc': min(created_values) if created_values else '',
        'window_end_utc': max(created_values) if created_values else '',
        'runs_listed': len(runs),
        'runs_with_claude_output_artifact': len(parsed_runs),
        'total_exact_cost_usd': sum(row['total_cost_usd'] for row in run_rows),
        'total_model_cost_usd': sum(row['model_cost_usd'] for row in run_rows),
        'total_subagent_estimated_cost_usd': sum(
            row['estimated_cost_usd'] for row in subagent_rows
        ),
        'total_subagent_allocated_run_cost_usd': sum(
            row['allocated_run_cost_usd'] for row in subagent_rows
        ),
        'conclusions': dict(sorted(conclusion_counts.items(), key=lambda item: item[0])),
        'notes': [
            'Run and model costs are exact values from claude-execution-output.json.',
            'Subagent reported_total_tokens comes from task progress notifications.',
            'Subagent estimated_cost_usd is derived from observed assistant usage.',
            'Subagent allocated_run_cost_usd prorates each run cost by reported_total_tokens.',
        ],
    }

    write_csv(output_dir / 'runs-costs.csv', run_rows)
    write_csv(output_dir / 'subagents-costs.csv', subagent_rows)
    write_csv(output_dir / 'models-costs.csv', model_rows)
    (output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
