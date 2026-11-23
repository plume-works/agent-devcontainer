# Backlog tasks

A backlog task is one small work item with a priority, which waits to become a
plan or a quick fix. A task that one session cannot complete becomes a plan.

- Path: `data/backlog/<slug>.md`.
- Hub: `data/backlog.md`.

``` yaml
---
type: task # required
stage: pending # required: see the table
priority: high # high | medium | low
created: 2026-08-01 # required, YYYY-MM-DD
completed: 2026-08-14 # set when the task is done
---
```

- `priority` is required on a new task.
- `rank` is optional. See `schema/build-order.md`.

| Stage       | Meaning                                 | Other fields               | Location        |
| ----------- | --------------------------------------- | -------------------------- | --------------- |
| `pending`   | Open                                    |                            | `data/backlog/` |
| `done`      | The work is complete, or a plan took it | `completed` set, no `rank` | Archive         |
| `cancelled` | The task was abandoned                  | No `rank`                  | Archive         |

Capture files a task at `pending`. The session that completes or abandons the
task closes it. Plan closes a task as `done` when a plan grows from it.

Body: an H1, then text that gives the work and why it is important.
