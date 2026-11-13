#!/usr/bin/env python3
"""
Summarise the spec audit rows beside this file.

Usage: aggregate.py [--per-spec] [--not-true] [--fate FATE]...

With no option it prints the counts of every labelled field. The field values are defined in
README.md.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

HERE = Path(__file__).parent
REQUIREMENT_FIELDS = ('subject', 'truth', 'test', 'adds', 'fate')
RATIONALE_FIELDS = ('kind', 'accurate', 'adr_worthy')
UNCHECKED = ('none', 'text-check')


def load(name: str) -> list[dict]:
    """Return the rows of one data file."""
    text = (HERE / f'{name}.jsonl').read_text()
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def counts(rows: list[dict], field: str) -> None:
    """Print how many rows carry each value of ``field``."""
    print(f'\n{field} (n={len(rows)})')
    for value, count in Counter(row.get(field) for row in rows).most_common():
        print(f'  {count:4} {100 * count / len(rows):5.1f}%  {value}')


def per_spec(requirements: list[dict], rationale: list[dict]) -> None:
    """Print one line of requirement and rationale counts for each spec."""
    by_spec = defaultdict(list)
    for row in requirements:
        by_spec[row['spec']].append(row)
    entries = Counter(row['spec'] for row in rationale)
    worthy = Counter(row['spec'] for row in rationale if row['adr_worthy'])
    print(f'\n{"spec":34} req not-true unchecked drop needs-test decision-records')
    for spec, rows in sorted(by_spec.items()):
        not_true = sum(row['truth'] != 'true' for row in rows)
        unchecked = sum(row['test'] in UNCHECKED for row in rows)
        drop = sum(row['fate'].startswith('drop') for row in rows)
        needs_test = sum(row['fate'] == 'needs-test' for row in rows)
        print(
            f'{spec:34} {len(rows):3} {not_true:8} {unchecked:9} {drop:4} {needs_test:10}'
            f' {worthy[spec]:5} of {entries[spec]}'
        )


def listing(rows: list[dict], note: str) -> None:
    """Print each row's spec, requirement title, and one of its note fields."""
    for row in rows:
        print(f'- {row["spec"]} :: {row["requirement"]}\n    {row.get(note, "")}')


def main() -> None:
    """Print the summaries the command line asks for."""
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('--per-spec', action='store_true', help='one line per spec')
    parser.add_argument('--not-true', action='store_true', help='requirements not fully true')
    parser.add_argument('--fate', action='append', default=[], help='requirements with this fate')
    args = parser.parse_args()
    requirements, rationale = load('requirements'), load('rationale')

    if args.per_spec:
        per_spec(requirements, rationale)
    if args.not_true:
        listing([row for row in requirements if row['truth'] != 'true'], 'truth_note')
    for fate in args.fate:
        listing([row for row in requirements if row['fate'] == fate], 'fate_note')
    if args.per_spec or args.not_true or args.fate:
        return

    scenarios = sum(row['scenarios'] for row in requirements)
    tested = sum(row['scenarios_tested'] for row in requirements)
    print(f'{len(requirements)} requirements, {scenarios} scenarios, {tested} with a test')
    for field in REQUIREMENT_FIELDS:
        counts(requirements, field)
    for field in RATIONALE_FIELDS:
        counts(rationale, field)
    print(f'\nrejected alternatives: {sum(row["rejected_count"] for row in rationale)}')


if __name__ == '__main__':
    main()
