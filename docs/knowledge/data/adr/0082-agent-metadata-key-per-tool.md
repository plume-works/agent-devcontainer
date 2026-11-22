---
type: adr
stage: accepted
---

# Each tool reads only its own key in `.agent.metadata.json`

Agent tools keep their metadata in `.agent.metadata.json` files. Each file is a
JSON object, and each top-level key belongs to one tool. A tool reads only its
own key and accepts the keys of other tools. As a result, one file can hold
metadata for tools that a checkout does not have. A tool reports a file that it
cannot parse as broken.

## Considered Options

- Skip a file that the tool cannot parse. Rejected: the tool would silently
  compute the wrong answer, for example report content as unchanged because the
  rule that would flag it never loaded.

## Consequences

- The `template-consume` key is the marker, which records the template state of
  a consumer. It is correct only in the root file, because a repository uses the
  template at one commit. The same key in a file in a subdirectory is broken
  metadata.
- The setup mode of `template-consume` writes the marker in the consumer. The
  template never copies it from this repository. As a result, the template
  classifies the root file by its top-level keys, not as one file.
