"""
Score every run record against its case's expected findings and write results.md.

Usage: report.py <corpus-dir>
"""

from collections import Counter
import json
from pathlib import Path
import re
import sys

PASS_ROLES = ('compliance', 'correctness', 'durable-knowledge')
LABELS = (
    ('P1', r'\bP1\b'),
    ('P2', r'\bP2\b'),
    ('P3', r'\bP3\b'),
    ('Question', r'\bQuestion\b'),
    ('non-blocking', r"non-?blocking|not blocking|doesn't block|does not block"),
    ('blocking', r'\bblocking\b|\bBlocking\b'),
)


def one_line(text: str, limit: int) -> str:
    """Collapse whitespace and cut to `limit` characters for a table cell."""
    flat = re.sub(r'\s+', ' ', str(text or '')).replace('|', '\\|').strip()
    return flat if len(flat) <= limit else flat[: limit - 1] + '…'


def label_of(body: str) -> str:
    """Read the severity label a comment opens with."""
    head = body[:300]
    for label, pattern in LABELS:
        if re.search(pattern, head):
            return label
    return 'unlabelled'


def matches(expected: dict, path: str, text: str) -> bool:
    """Whether a comment or candidate is the expected finding."""
    path = path or ''
    if expected.get('path_include') and expected['path_include'] not in path:
        return False
    if expected.get('path_exclude') and expected['path_exclude'] in path:
        return False
    return re.search(expected['match'], text or '', re.IGNORECASE) is not None


def gate_stopped(record: dict) -> bool:
    """Tell whether a review ended without dispatching a pass: a metadata stop or fast approve."""
    return record['review'] is not None and not any(
        s['role'] in PASS_ROLES for s in record['subagents']
    )


def score(record: dict, expected: dict) -> str:
    """One cell: what the run did with one expected finding."""
    if expected['expect'] == 'gate-stop':
        return 'stopped' if gate_stopped(record) else 'not stopped'
    review = record['review'] or {}
    for comment in review.get('comments', []):
        if matches(expected, comment.get('path'), comment.get('body')):
            return f'posted ({label_of(comment["body"])})'
    for candidate in record['candidates'] or []:
        if candidate.get('posted'):
            continue
        if matches(expected, candidate.get('path'), candidate.get('claim')):
            return 'dropped'
    return 'not raised'


def event_of(review: dict | None) -> str:
    """Name what a run would post; the `cr` arm writes `issues` in place of a review."""
    if review is None:
        return 'no review'
    if 'issues' in review:
        return f'{len(review["issues"])} issues'
    return review.get('event', 'no event')


def passes_summary(record: dict) -> str:
    """Count the subagents per role and the model each actually ran on."""
    counts = Counter(
        (s['role'], '+'.join(m.removeprefix('claude-') for m in s['actual_models']) or '?')
        for s in record['subagents']
    )
    return ', '.join(f'{role} {n}× {model}' for (role, model), n in sorted(counts.items()))


def run_details(record: dict, expected: list[dict]) -> list[str]:
    """List the posted comments and the dropped candidates of one run."""
    review = record['review'] or {}
    lines = [
        '<details>',
        f'<summary>{record["run"]}: {event_of(record["review"])}, '
        f'{len(review.get("comments", []))} comments</summary>',
        '',
        f'Body: {one_line(review.get("body"), 600) or "(none)"}',
        '',
        '| Posted comment | File | Label | Text |',
        '| --- | --- | --- | --- |',
    ]
    for i, comment in enumerate(review.get('comments', []), 1):
        known = [
            e['id']
            for e in expected
            if 'match' in e and matches(e, comment.get('path'), comment.get('body'))
        ]
        lines.append(
            f'| {i} {" ".join(known)} | `{Path(comment.get("path", "")).name}` '
            f'| {label_of(comment.get("body", ""))} | {one_line(comment.get("body"), 400)} |'
        )
    dropped = [c for c in record['candidates'] or [] if not c.get('posted')]
    if dropped:
        lines += [
            '',
            '| Dropped candidate | Pass | File | Claim | Validator |',
            '| --- | --- | --- | --- | --- |',
        ]
        for i, cand in enumerate(dropped, 1):
            known = [
                e['id']
                for e in expected
                if 'match' in e and matches(e, cand.get('path'), cand.get('claim'))
            ]
            lines.append(
                f'| {i} {" ".join(known)} | {one_line(cand.get("pass") or cand.get("agent"), 30)} '
                f'| `{Path(str(cand.get("path"))).name}` | {one_line(cand.get("claim"), 300)} '
                f'| {one_line(cand.get("validation"), 300)} |'
            )
    lines += ['', '</details>', '']
    return lines


def main() -> None:
    """Write results.md from the corpus."""
    corpus = Path(sys.argv[1])
    rounds = json.loads((corpus / 'rounds.json').read_text())
    variants = {v['id']: v for v in json.loads((corpus / 'variants.json').read_text())}
    out = [
        '# pr-review replay results',
        '',
        'Generated by `tools/report.py` from `runs/`, `cases/`, `variants.json` and '
        '`rounds.json`; do not edit by hand.',
        '',
    ]
    for rnd in rounds:
        out += [f'## Round {rnd["round"]}', '', rnd['question'], '']
        for arm in rnd['arms']:
            v = variants[arm]
            where = f'`{v["commit"][:8]}` on base `{v["base"][:8]}`' if v['commit'] else ''
            diff = f', [diff]({v["diff"]})' if v['diff'] else ''
            out.append(f'- `{arm}`: {v["change"]} {where}{diff}')
        out += [
            '',
            '| Case | Expected finding | ' + ' | '.join(f'`{a}`' for a in rnd['arms']) + ' |',
            '| --- | --- |' + ' --- |' * len(rnd['arms']),
        ]
        for case in rnd['cases']:
            spec = json.loads((corpus / 'cases' / case / 'case.json').read_text())
            for exp in spec['expected']:
                cells = []
                for arm in rnd['arms']:
                    runs = sorted((corpus / 'runs' / arm).glob(f'{case}-{arm}-*.json'))
                    tally = Counter(
                        score(json.loads(r.read_text()), exp).split(' ')[0] for r in runs
                    )
                    cells.append(
                        ', '.join(f'{k} {n}/{len(runs)}' for k, n in sorted(tally.items()))
                    )
                out.append(f'| {case} | {exp["id"]} | ' + ' | '.join(cells) + ' |')
        out.append('')
        for case in rnd['cases']:
            spec = json.loads((corpus / 'cases' / case / 'case.json').read_text())
            expected = spec['expected']
            out += [f'### Round {rnd["round"]}: {case}', '']
            head = ['Run', 'Event', 'Passes (role, count, model run)', 'Cost', 'Time']
            head += [e['id'] for e in expected]
            out += ['| ' + ' | '.join(head) + ' |', '|' + ' --- |' * len(head)]
            details = []
            for arm in rnd['arms']:
                for path in sorted((corpus / 'runs' / arm).glob(f'{case}-{arm}-*.json')):
                    rec = json.loads(path.read_text())
                    row = [
                        rec['run'],
                        event_of(rec['review']),
                        passes_summary(rec) or '—',
                        f'${rec["cost_usd"]:.2f}',
                        f'{rec["duration_s"] // 60}m',
                    ]
                    row += [score(rec, e) for e in expected]
                    out.append('| ' + ' | '.join(row) + ' |')
                    details += run_details(rec, expected)
            out += [''] + details
    text = '\n'.join(line.rstrip() for line in out).rstrip() + '\n'
    (corpus / 'results.md').write_text(text)


if __name__ == '__main__':
    main()
