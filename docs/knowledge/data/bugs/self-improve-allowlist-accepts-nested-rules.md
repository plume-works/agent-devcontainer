---
type: bug
description: The self-improve mutator must accept only rules/*.md, but allowlist._kind_of accepts a rule file in any subdirectory of rules/.
stage: pending
severity: low
sources:
- resource: .agents/plugins/self-improve/selfimprove/allowlist.py
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the self-improve allowlist accepts a rule at any depth below `rules/`

## Symptom

The mutator must accept a rule only at `rules/*.md` and reject each other path.
It accepts a path such as `.claude/rules/sub/deep/x.md` as a rule, so a proposal
can write a rule file in a subdirectory.

## Reproduction

1. Give `.agents/plugins/self-improve/selfimprove/allowlist.py::_kind_of` the
   project path `.claude/rules/sub/deep/x.md`.
2. It returns the rule kind, and does not raise `PathRejected`.

## Root cause

`.agents/plugins/self-improve/selfimprove/allowlist.py::_kind_of` accepts
`len(parts) >= 2` with `parts[0] == 'rules'` and a `.md` last part. It checks
the name of each part, but not the number of parts.
