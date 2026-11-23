---
type: adr
stage: accepted
---

# The catalog has no template consumption skill

Another repository adopts agentdev by pointing its descriptor at the published
`agentdev-devcontainer` image or by deriving its own image from it. The catalog
ships no skill that copies this repository's template surface into a consumer or
diffs that surface on update, and no repository keeps a `template-consume`
marker in `.agent.metadata.json`. The user decided that full-copy adoption is
not worth maintaining.

## Consequences

- The consequences of ADR-0043, ADR-0048, and ADR-0082 that name
  `template-consume`, `tracked_paths`, or the consumption guide no longer apply;
  their decisions stand.
