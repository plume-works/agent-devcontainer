# Features

A feature is a proposal: what users must get, written before the work. After its
plan ships, the code and its tests give the behaviour, and the feature goes to
the archive.

- Path: `data/features/<slug>.md`.
- Hub: `data/features.md`.

``` yaml
---
type: feature # required
stage: accepted # required: see the table
---
```

| Stage         | Meaning                               | Set by  | Location         |
| ------------- | ------------------------------------- | ------- | ---------------- |
| `proposed`    | Filed, with no plan                   | Capture | `data/features/` |
| `accepted`    | A plan lists the feature in `release` | Plan    | `data/features/` |
| `implemented` | The plan shipped                      | Ship    | Archive          |
| `deprecated`  | The behaviour is no longer wanted     |         | Archive          |
| `cancelled`   | The proposal was abandoned            |         | Archive          |

Body: `## Purpose`, `## Behaviour`, `## Edge cases`, and `## Open questions`,
all required, in this order. An `## Open questions` section with no open
question says so in one line. Other sections can come after these.
