---
type: codebase
description: The licensed starter IWE data tree copied into consumers that adopt project memory, with placeholders and examples for the onboarding skills to replace.
source: templates/iwe
source_digest: sha256:04f90a04e72831949f088835c16d4478adf0206a9afb07330f9190525fa80400
verified:
  by: codex/gpt-5
  at: 2026-09-06T19:05:00Z
stale_after: 2026-12-05
generated:
  by: codex/gpt-5
  at: 2026-09-06T19:05:00Z
sources:
- id: code
  resource: templates/iwe
---

# Consumer IWE seed

The starter `docs/knowledge/data/` tree for repositories that adopt the
template's knowledge-base bundle. It includes the license, graph hubs,
onboarding tasks, placeholders, and fictional examples needed before `iwe-setup`
replaces them with project-specific knowledge.

## Public surface

- `templates/iwe/data/` — the complete starter OKF bundle copied into a consumer
- `templates/iwe/LICENSE.md` — the MIT notice copied beside the consumer graph
- `templates/iwe/data/product.md` — product placeholders filled by `iwe-setup`
- `templates/iwe/data/backlog/fill-product-doc.md` and
  `capture-current-architecture.md` — onboarding task keys closed by setup
- `templates/iwe/data/**/*.example.md` — document-shape examples removed after
  onboarding

## How it works

[Template consumption](../agents/plugins/agentdev/skills.md) copies `data/` and
the license into a consumer that keeps IWE, then invokes `iwe-setup` followed by
`iwe-map`. The [knowledge workspace](../docs/knowledge.md) tests the seed by
assembling it under a temporary consumer layout with this repository's `.iwe/`
schemas and running the same validation and normalization gates.

## Depends on

The root `.iwe/` schemas define every accepted document shape; `iwe-setup` owns
placeholder replacement and example removal, and `iwe-map` fills the empty map.

## Invariants & gotchas

- The seed is not part of this repository's own graph and is never updated by
  root-level `iwe normalize`.
- Consumer project memory is seeded once. Template update mode never compares,
  replaces, or reseeds `docs/knowledge/data/`.
- Workflow state is named by `stage`; reference examples carry `type` and no
  stage, matching the schemas consumers validate against.
- `fill-product-doc` and `capture-current-architecture` are interface keys for
  `iwe-setup`; renaming either breaks onboarding.

## Key references

Verified anchor points (line numbers as of 2026-09-06):

- `templates/iwe/README.md:3` — seed role and destination
- `templates/iwe/README.md:21-27` — placeholders, tasks, and examples
- `templates/iwe/README.md:42-49` — graph and formatter boundaries
- `templates/iwe/data/backlog/fill-product-doc.md:12` — setup task key
- `templates/iwe/data/backlog/capture-current-architecture.md:12` — architecture
  task key
