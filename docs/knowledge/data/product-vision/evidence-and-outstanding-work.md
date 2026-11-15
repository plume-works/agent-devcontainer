---
type: product-vision
description: A report on the state of work keeps what is done apart from what is still to do, and states only what no check or other document states.
sources:
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: .agents/plugins/agentdev/skills/code-review-standards/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
---

# Evidence and outstanding work

A document that reports on the state of work, such as a plan, a pull request
body, or a release page, must let the reader know on each line one of two
things. Either the line tells the reader a fact, or it gives the reader work to
do.

## Done and not done stay apart

Evidence is a command that ran and a result that the writer read. Work that
somebody must still do is never written as evidence. An item that only a party
outside the session can close, such as a CI run, a review, or a person with
special access, stays open and names that party.

## A document states only what nothing else states

A check that runs on each push is better evidence than a sentence that says the
same thing. A fact that another document owns is linked, not copied. What
remains after these two cuts is the part that a reader must read.

The `pr-gen-description` and `code-review-standards` skills apply these
principles to pull request bodies. The `iwe-verifier` and `iwe-shipper`
rulebooks apply them to plans.
