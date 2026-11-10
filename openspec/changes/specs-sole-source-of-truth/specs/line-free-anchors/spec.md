# Spec Delta

## MODIFIED Requirements

### Requirement: A gate rejects line-number references

`scripts/check-anchors.py`, run by an always-run pre-commit hook and therefore
by the CI pre-commit job, SHALL fail on every `file.ext:N` or `file.ext:N-M`
reference, extensionless `Dockerfile`, `Makefile`, or `Containerfile` `:N`
reference, `#LN` fragment, and prose `line N` or `lines N` in
`docs/knowledge/data/`, in `openspec/`, and in the agentdev catalog's skills
and agents, fenced blocks included, and SHALL list every violation. It cannot see chat reports,
code comments, or PR bodies; those rest on the catalog's instructions.

#### Scenario: A plan cites a line

- **WHEN** a commit adds a `scripts/x.py:<number>` reference to any graph
  document
- **THEN** the hook fails and names the document

#### Scenario: A reference uses an anchor

- **WHEN** a document cites `<path>.py::main` or `<file>.md#usage`
- **THEN** the gate passes it

#### Scenario: A spec cites a line

- **WHEN** a commit adds a `scripts/x.py:<number>` reference to a spec under
  `openspec/specs/` or to an OpenSpec change
- **THEN** the hook fails and names the document

### Requirement: Live anchors resolve

The same script SHALL resolve every anchor under `## Key references` in a plan
without `stage`, and every anchor in a bug or backlog item at `stage: pending`
or `stage: planned` and in every spec under `openspec/specs/`, against the
current checkout, and SHALL fail naming each anchor that does not resolve. A Python
symbol resolves through its syntax tree; a symbol in any other language resolves
when each dotted segment occurs as a whole word in order, so a symbol moved into
a comment still resolves. A quote resolves when it occurs, whitespace-collapsed,
in the anchored region. Anchors elsewhere in a plan, in closed documents, in
findings, and in OpenSpec changes are not resolved.

#### Scenario: A refactor renames an anchored function

- **WHEN** a commit renames a function an active plan's `## Key references` or
  a spec under `openspec/specs/` anchors
- **THEN** the hook fails naming the document and the anchor, until the anchor
  is updated

#### Scenario: A plan names code it will create

- **WHEN** an active plan's task names `<new-file>.py::main`, which does not
  exist yet
- **THEN** the resolver does not check it, because it is outside
  `## Key references`

#### Scenario: A shipped plan names deleted code

- **WHEN** a plan with `stage: done` anchors a file that has since been deleted
- **THEN** the resolver does not check it
