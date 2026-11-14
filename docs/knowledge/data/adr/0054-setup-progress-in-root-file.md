---
type: adr
stage: accepted
description: The template setup progress lives in the root file .agentdev-template-progress.md, and consumed_ref stays in the marker in .agent.metadata.json.
---

# Setup progress is a root file and the Git reference of the consumed commit stays in JSON

The progress document is `.agentdev-template-progress.md` at the root of the
consumer. The IWE graph of the consumer does not exist before the bootstrap
task, and a consumer without IWE never has one. `consumed_ref` stays in the
marker, because JSON has one parse with one failure result, `INVALID_MARKER`.

## Considered Options

- The progress record in the IWE graph of the consumer. Rejected: the graph does
  not exist during bootstrap, or ever for a consumer without IWE.
- Read the consumed commit from the progress document. Rejected: a commit SHA in
  prose has no parse and no failure result. If the recorded commit moves to a
  wrong commit, the update misses upstream changes and nothing shows it.
- A copy of the task list in the knowledge-base summary. Rejected: the two
  copies become different.

## Consequences

- The consumer owns `.agentdev-template-progress.md`. Git tracks it, a template
  update keeps it, and it is never in `tracked_paths`.
- The `template-consume` key of `.agent.metadata.json` is state that the setup
  of the consumer writes. The setup never copies it from the publisher.
