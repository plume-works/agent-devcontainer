---
type: adr
stage: deprecated
---

# Setup progress is a root file and the consumed ref stays in JSON

The progress document is `.agentdev-template-progress.md` at the root of the
consumer. The IWE graph of the consumer does not exist until the bootstrap task,
itself one of the setup tasks, and a consumer that declines IWE never has one; a
root file serves both. `consumed_ref` stays in the marker, the
`template-consume` key of `.agent.metadata.json`, because JSON has one parse
with one failure result, `INVALID_MARKER`.

## Considered Options

- The progress record in the IWE graph of the consumer. Rejected: the graph does
  not exist during bootstrap, or ever for a consumer without IWE.
- Read the consumed commit from the progress document. Rejected: a commit SHA in
  prose has no parse and no failure result, and a wrongly advanced ref silently
  skips upstream changes on every later update.

## Consequences

- The consumer owns `.agentdev-template-progress.md`. Git tracks it, a template
  update keeps it, and it is never in `tracked_paths`.
- The `template-consume` key of `.agent.metadata.json` is state that the setup
  of the consumer writes. The setup never copies it from this repository.
