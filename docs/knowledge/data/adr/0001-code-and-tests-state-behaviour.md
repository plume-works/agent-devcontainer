---
type: adr
stage: accepted
description: Code and tests are the only statement of how the product behaves; ADRs hold the reasons and the glossary holds the terms.
---

# Code and tests are the only statement of behaviour

`data/spec/` states the behaviour of the repository a second time in prose, and
[the spec usefulness audit](../findings/spec-usefulness-audit.md) found that 207
of its 264 requirements repeat a test, a rulebook, or plain code, and that 34
are not fully true. Code and tests are the only statement of behaviour, ADRs
hold the reasons, and the glossary holds the terms, because a statement that no
test runs moves away from the code.

## Considered Options

- Keep the specs and merge each change into them at ship. Rejected: the merge is
  a careful reading, and nothing fails when it is wrong.
- Keep a spec only for behaviour that no test can reach. Rejected: the rulebook
  is that text already.

## Consequences

- The behaviour of a rulebook has no test. A plan states it as acceptance
  scenarios, Verify checks them one time at ship, and then they stay only in the
  archived plan.
- `data/spec/` gets no new text.
