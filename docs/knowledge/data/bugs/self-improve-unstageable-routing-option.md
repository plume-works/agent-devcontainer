---
type: bug
stage: pending
severity: medium
description: The improve skill offers a routing option — add or patch a linked reference — that the path allowlist cannot resolve, so choosing it is rejected as bad_kind.
sources:
- resource: .agents/plugins/self-improve/skills/improve/SKILL.md
- resource: .agents/plugins/self-improve/selfimprove/allowlist.py
---

# Bug: Unstageable routing option in the improve skill

## Symptom

The `improve` skill's routing list offers four options and instructs the model
to stop at the first that fits. The third — add or patch a linked reference
owned by an umbrella — names no artifact the mutator can stage. A lesson routed
there cannot become a proposal.

The instruction is followed by a model choosing in good faith between four
options presented as equivalent, and one of them has no destination.

## Reproduction

`.agents/plugins/self-improve/skills/improve/SKILL.md#2-find-the-owner › "Add or patch a linked reference** owned by such an"`
offers:

``` text
3. **Add or patch a linked reference** owned by such an umbrella.
```

`candidate_paths` resolves exactly three kinds — `CLAUDE.md`, `rule`, and
`skill` — and raises `PathRejected('bad_kind')` for anything else. A linked
reference is none of the three: it is an arbitrary path a `CLAUDE.md` or rule
happens to point at, so it has no shape the allowlist can express.

## Root cause

The routing preference order is transcribed from the design, where four options
are described as a preference order for a human reader. The allowlist implements
three, because the fourth has no bounded path shape: allowing an arbitrary
linked file would mean accepting any path an instruction file references, which
is the property the allowlist exists to deny.

So the skill and the mutator disagree about how many destinations exist, and the
skill is the copy a model reads while choosing.

## Potential solution

The two ways to close it are to drop option 3 from the skill, leaving three
options that all resolve, or to give linked references a bounded shape the
allowlist can express and implement that kind.

Dropping it is the smaller change and loses only an option that never worked.
Implementing it is a widening of the mutation surface and needs its own decision
about what shape a linked reference may take, which is out of scope for a move
that changes no behavior.

## Key references

- `.agents/plugins/self-improve/skills/improve/SKILL.md#2-find-the-owner › "Add or patch a linked reference** owned by such an"`
  — the routing option that cannot be staged
- `.agents/plugins/self-improve/selfimprove/allowlist.py::candidate_paths` —
  `candidate_paths` and the three kinds it resolves
- `.agents/plugins/self-improve/selfimprove/allowlist.py::candidate_paths` — the
  `bad_kind` rejection every other target reaches
