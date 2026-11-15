---
type: task
stage: done
created: 2026-11-15
completed: 2026-11-15
---

# Plan Tasks evidence and ADRs as git history

A new format for tasks completions/evidence - a git commit message. Instead of
writing evidence into the plan, implementer ticks off the task and commits with
message like:

```
Bla-bla-bla according to regular commit rules.

---
Task N - finished.
<Evidence prose>
```

Since plan's task list tick is in the same commit, it is linked from now on.
Discvoverable on a moment notice since its linked to code too. So decisions of
agent at the moment are also tracked.

PR goes like normal. Squish merge has a normal PR body - which is a lasting
summary. No ADR is needed for what is stated in PR body, since it is a body of
squished commit. Extra advantage to is that when code changes, it is
automatically linked to decision chain through git history. And it should reduce
agent's overwhelm with conflicting ADRs. Git has much richer info. And if more
info needed. Pr-reconnect script should easily get the full history of that PR
into the tree for analysis
