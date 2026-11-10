# Line-free anchors Specification

## Purpose

A line number is wrong the next time its file changes. This specifies how every
reference names a place in a file instead, and the gate that keeps line numbers
out of the graph and the agentdev catalog.

## Requirements

### Requirement: References never record a line number

Every reference to a place in a file that is committed or published — graph
documents, catalog skills and agents, code comments, PR and issue bodies — and
every skill or agent chat report SHALL name the place by an anchor and SHALL
never record a line number. An anchor is `path::symbol` in code,
`path#heading-slug` in Markdown, `path#key.path` in YAML, JSON, and TOML (a list
element named by its `id` or `name`), `path#target` or `path#stage` in a
Makefile or Dockerfile, any of those followed by ` › "verbatim quote"` for a
spot inside it, or a bare `path` for a whole file. Only machine positions keep a
line: the `line` GitHub's review API needs to place an inline comment, and raw
tool output, which a report never quotes with its line numbers.

#### Scenario: A plan names the code it touches

- **WHEN** Plan writes `## Key references`
- **THEN** each entry is an anchor taken from the current checkout, with no line
  number and no date stamp

#### Scenario: A verifier cites evidence

- **WHEN** Verify, Ship, or an adversarial review reports a finding
- **THEN** its evidence names the code or document by anchor, never by line

#### Scenario: A pull request review comments inline

- **WHEN** `pr-review` posts a finding as an inline comment
- **THEN** the API call carries the line that places the comment, and the
  comment text and the review body name every location by anchor

### Requirement: A gate rejects line-number references

`scripts/check-anchors.py`, run by an always-run pre-commit hook and therefore
by the CI pre-commit job, SHALL fail on every `file.ext:N` or `file.ext:N-M`
reference, extensionless `Dockerfile`, `Makefile`, or `Containerfile` `:N`
reference, `#LN` fragment, and prose `line N` or `lines N` in
`docs/knowledge/data/` and in the agentdev catalog's skills and agents, fenced
blocks included, and SHALL list every violation. It cannot see chat reports,
code comments, or PR bodies; those rest on the catalog's instructions.

#### Scenario: A plan cites a line

- **WHEN** a commit adds a `scripts/x.py:<number>` reference to any graph
  document
- **THEN** the hook fails and names the document

#### Scenario: A reference uses an anchor

- **WHEN** a document cites `scripts/x.py::main` or `README.md#usage`
- **THEN** the gate passes it

### Requirement: Live anchors resolve

The same script SHALL resolve every anchor under `## Key references` in a plan
without `stage`, and every anchor in a bug or backlog item at `stage: pending`
or `stage: planned` and in every `architecture/` document, against the current
checkout, and SHALL fail naming each anchor that does not resolve. A Python
symbol resolves through its syntax tree; a symbol in any other language resolves
when each dotted segment occurs as a whole word in order, so a symbol moved into
a comment still resolves. A quote resolves when it occurs, whitespace-collapsed,
in the anchored region. Anchors elsewhere in a plan, and in closed documents,
are not resolved.

#### Scenario: A refactor renames an anchored function

- **WHEN** a commit renames a function an active plan's `## Key references` or
  an `architecture/` document anchors
- **THEN** the hook fails naming the document and the anchor, until the anchor
  is updated

#### Scenario: A plan names code it will create

- **WHEN** an active plan's task names `scripts/new.py::main`, which does not
  exist yet
- **THEN** the resolver does not check it, because it is outside
  `## Key references`

#### Scenario: A shipped plan names deleted code

- **WHEN** a plan with `stage: done` anchors a file that has since been deleted
- **THEN** the resolver does not check it
