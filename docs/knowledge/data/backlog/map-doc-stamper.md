---
type: task
description: Bundle a script with the iwe-map skill that writes a refreshed map doc's current source_digest, verified, stale_after, generated, and anchor date in one step.
stage: planned
priority: low
created: 2026-10-29
generated:
  by: claude-code/opus-5.5
  at: 2026-10-29T18:56:30Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-map/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py
---

# Bundle a map-doc stamper with the iwe-map skill

A refresh in `/agentdev:iwe-map` step 8 ends each `STALE` doc by bumping
`source_digest`, `verified`, `stale_after`, and `generated`, and the
`Verified anchor points` date. The skill gives no tool for it: the agent copies
the digest out of `stale-map-docs.py`'s `STALE` line and edits four frontmatter
fields by hand per doc, which is slow over a multi-doc refresh and easy to get
wrong — a mistyped digest or a stale `stale_after` passes `iwe schema validate`
and only shows up on the next freshness check.

The work: add an `agent-code/` script to the skill that takes map-doc keys,
reads each doc's current digest from `stale-map-docs.py`, and writes the four
fields plus the anchor date, following the `/agentdev:skill-scripts` output
contract (`RESULT=` line, shared exit codes); refuse a key that is not `STALE`
rather than stamping a doc nobody re-read; document it in step 8; and cover it
with plugin tests. It stamps only — re-reading the code and rewriting prose
stays the agent's job.

## Prototype

Run from the repository root as `stamp.py <key>...`. It hard-codes the actor,
the 90-day window, and the frontmatter layout, and stamps without checking the
key is `STALE`:

``` python
"""Stamp map docs with their current source digest, verified, stale_after, and generated."""

import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
ACTOR = 'claude-code/opus-5.5'
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
stale_after = (datetime.date.today() + datetime.timedelta(days=90)).isoformat()
out = subprocess.run(
    [str(ROOT / '.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py')],
    capture_output=True,
    text=True,
).stdout
current = {
    m.group(1): m.group(2) for m in re.finditer(r'^STALE (\S+) source_digest (\S+)$', out, re.M)
}
for key in sys.argv[1:]:
    path = ROOT / 'docs/knowledge' / f'{key}.md'
    text = path.read_text()
    head, body = text.split('\n---\n', 1)
    head = re.sub(r'^source_digest: .*$', f'source_digest: {current[key]}', head, flags=re.M)
    head = re.sub(
        r'^verified:\n  by: .*\n  at: .*$',
        f'verified:\n  by: {ACTOR}\n  at: {now}',
        head,
        flags=re.M,
    )
    head = re.sub(
        r'^generated:\n  by: .*\n  at: .*$',
        f'generated:\n  by: {ACTOR}\n  at: {now}',
        head,
        flags=re.M,
    )
    head = re.sub(r'^stale_after: .*$', f'stale_after: {stale_after}', head, flags=re.M)
    body = re.sub(r'line numbers as of \d{4}-\d{2}-\d{2}', f'line numbers as of {now[:10]}', body)
    path.write_text(head + '\n---\n' + body)
    print('stamped', key)
```
