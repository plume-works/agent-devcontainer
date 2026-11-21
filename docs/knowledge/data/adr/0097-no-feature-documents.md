---
type: adr
stage: accepted
description: The knowledge base has no feature document type; a plan's acceptance scenarios state what users get, and archived features stay as history.
---

# The knowledge base has no feature documents

A feature document repeated what the plan's `## Acceptance` scenarios already
state, and the release cut writes the release page from those scenarios, not
from features. Thus `feature` is a retired type, like `architecture`: valid only
under `data/archive/`, and a plan's `release` lists only the bugs it closes.
This is the decision of the maintainer.

## Considered Options

- Features as the long-lived document for a capability, with stories that
  advance them. Rejected with the backlog task that proposed it: the plan and
  the code already carry what a feature held.
