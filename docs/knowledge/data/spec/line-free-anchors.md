---
type: spec
description: References name a place by symbol, heading slug, key path, or verbatim quote, never by line number, and a pre-commit gate rejects line numbers and resolves live anchors.
sources:
- resource: AGENTS.md
- resource: scripts/check-anchors.py
- resource: .pre-commit-config.yaml
- resource: docs/knowledge/AGENTS.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
---

# Line-free anchors

## Purpose

A line number is wrong the next time its file changes. This specifies how every
reference names a place in a file instead, and the gate that keeps line numbers
out of the graph and the agentdev catalog.

## Rationale

### Places are named by anchors, and a gate holds the rule

The maintainer's rule is never to record a line number. An anchor stays true
until its target is renamed or removed and then stops resolving rather than
silently pointing elsewhere, so it carries no date stamp. The gate runs on every
commit rather than behind a path filter, because a code rename anywhere can
break a live anchor.

The gate's limits are accepted rather than closed: it does not recognize a bare
`:N` continuing an earlier reference; a non-Python symbol resolves by its dotted
segments occurring as whole words in order, so a symbol moved into a comment
still resolves; and chat reports, code comments, and PR bodies rest on the
catalog's instructions. A link into another repository's file at a pinned commit
may keep its line fragment, since that target cannot change and an anchor names
only this repository's code; the research case studies under `docs/research/`
cite sources that way and are outside the gate. A placeholder in a resolved
document is written in angle brackets so the resolver does not read it as a
path.

Rejected:

- **Line numbers with a date stamp.** The stamp tells a reader how far to trust
  the number but does not keep it true.
- **Planting anchors in target files** (`<a id>`, `anchor:` comments). Every
  reference would edit the file it points at, while a symbol or heading already
  identifies the spot.
- **Exempting closed documents from the line-number gate.** Agents copy the
  shape they read, and the exemption would need its own rule.
