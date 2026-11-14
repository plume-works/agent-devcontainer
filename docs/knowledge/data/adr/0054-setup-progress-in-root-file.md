---
type: adr
stage: accepted
description: The template setup progress lives in the root file .agentdev-template-progress.md, and consumed_ref stays in the marker in .agent.metadata.json.
---

# Setup progress is a root file and the consumed ref stays in JSON

The progress document is `.agentdev-template-progress.md` at the root of the
consumer. The IWE graph of the consumer does not exist before the bootstrap
task, and a consumer without IWE never has one. `consumed_ref` stays in the
marker, because JSON has one parse with one failure result, `INVALID_MARKER`.

## Considered Options

- The progress record in the IWE graph of the consumer. Rejected: the graph does
  not exist during bootstrap, or ever for a consumer without IWE.
- Read the consumed commit from the progress document. Rejected: a commit SHA in
  prose has no parse and no failure result. A wrong advance skips upstream
  changes and nothing shows it.
- A copy of the task list in the knowledge-base summary. Rejected: the two
  copies become different.
