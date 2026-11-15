---
type: adr
stage: proposed
description: An agent looks for an answer in the code first, in the git history second, and in a document last, and the pull request body states each decision so that the squash commit holds it.
---

# Code first, git history second, documents last

A document becomes incorrect when nobody maintains it, and an ADR is a document
too. The code and the git history stay correct without maintenance. Thus an
agent looks for an answer in the code first, then in the git history, and in a
document last, and it does not fully trust a document. Each pull request body
states the decisions of its change, with the reason and the rejected options,
because the squash commit message is the pull request body.

## Considered Options

- Documents first. Rejected: the specs that the code contradicted were the first
  source, and an agent read them as true.
- Pull request bodies in place of ADRs now. Rejected for now: the ADRs stay
  until the pull request bodies hold the decisions. [Archive ADRs when their
  plans ship](../someday/archive-adrs-when-their-plans-ship.md) is the next
  step.

## Consequences

- A pull request body and an ADR state the same decision. This copy is
  intentional.
- [Evidence and outstanding work](../concept/evidence-and-outstanding-work.md)
  permits the copy of a decision in a pull request body.
