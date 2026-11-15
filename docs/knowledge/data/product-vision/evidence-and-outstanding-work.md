---
type: product-vision
description: A report on the state of work keeps what is done apart from what is still to do. It states only what no check or other document states.
sources:
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: .agents/plugins/agentdev/skills/code-review-standards/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
---

# Evidence and outstanding work

Some documents give the state of work, for example a plan, a pull request body,
or a release page. Each line of such a document must do one of two things.
Either the line tells the reader a fact, or it gives the reader work to do.

## Done and not done stay apart

Evidence is a command that ran and a result that the writer read. A writer never
records work that somebody must still do as evidence. Some items can close only
from outside the session, for example by a CI run, a review, or a person with
special access. Such an item stays open and names who closes it.

## A document states only what nothing else states

A check that runs on each push is better evidence than a sentence that says the
same thing. When another document records a fact, the writer links to that
document and does not copy the fact. After the writer removes these two types of
text, the text that remains is the part that a reader must read.

The `pr-gen-description` and `code-review-standards` skills apply these
principles to pull request bodies. The `iwe-verifier` and `iwe-shipper`
rulebooks apply them to plans.
