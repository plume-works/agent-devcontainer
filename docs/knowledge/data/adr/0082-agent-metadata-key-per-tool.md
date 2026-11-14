---
type: adr
stage: accepted
description: An `.agent.metadata.json` file is a JSON object with one top-level key for each tool, and a tool reports a file that it cannot parse as broken.
---

# Each tool reads only its own key in `.agent.metadata.json`

Agent tools keep their metadata in `.agent.metadata.json` files. Each file is a
JSON object, and each top-level key belongs to one tool. A tool reads only its
own key and accepts the keys of other tools. As a result, one file can hold
metadata for tools that a checkout does not have.

## Considered Options

- Do not use a file that the tool cannot parse. Rejected: the tool then gives an
  incorrect result and shows no error, because it did not read a rule in that
  file.

## Consequences

- The `template-consume` key is the marker, and it is correct only in the root
  file.
  `.agents/plugins/agentdev/skills/template-consume/agent-code/check-updates.py::read_marker`
  stops with `INVALID_MARKER` for a file that it cannot parse, and with
  `NO_MARKER` when the file has no `template-consume` key.
