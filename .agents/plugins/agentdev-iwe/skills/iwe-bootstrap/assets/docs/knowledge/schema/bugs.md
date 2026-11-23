# Bugs

A bug is a defect in shipped behaviour: behaviour that is incorrect and that a
reader can reproduce, or code that does not agree with an accepted ADR. A bug
holds the report and the investigation.

- Path: `data/bugs/<slug>.md`.
- Hub: `data/bugs.md`.

``` yaml
---
type: bug # required
stage: pending # required: see the table
severity: high # critical | high | medium | low — required
---
```

- `severity` is the impact of the defect — how bad it is when it happens — not
  its urgency. It is descriptive only and does not set `rank`.
- `rank` is optional. See `schema/build-order.md`.

| Stage       | Meaning                           | Set by                                             | Location     |
| ----------- | --------------------------------- | -------------------------------------------------- | ------------ |
| `pending`   | Open, with no plan                | Capture; Ship or Plan, when the plan drops the bug | `data/bugs/` |
| `planned`   | A plan lists the bug in `release` | Plan                                               | `data/bugs/` |
| `done`      | Fixed                             | Ship; Capture, when the same change fixed it       | Archive      |
| `cancelled` | The bug will not be fixed         |                                                    | Archive      |

Body: an H1 that starts with `Bug: `. Then `## Symptom`, `## Reproduction`, and
`## Root cause`, all required, in this order. Then two optional sections, in
this order. Other sections can come after these.

- `## Potential solution` — the direction that is intended, at any stage.
- `## Fix` — the fix that shipped, in a few sentences. A bug at `done` has it.
  The session that fixed the bug directly writes it. If a plan fixed the bug,
  Ship writes it from that plan and links that plan.

A `## Reproduction` or a `## Root cause` that is not yet known is never only
"unknown". It gives what is known, each hypothesis that was eliminated and what
eliminated it, and a link to the backlog task whose spike settles it. No section
gives the lifecycle of the bug: `stage` does.
