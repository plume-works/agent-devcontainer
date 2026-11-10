# Spec Delta

## Purpose

Says where each kind of durable project knowledge lives — behavior in OpenSpec
specs, the reasoning behind it beside those specs, findings in the knowledge
graph, procedures in `docs/` — so every fact has exactly one home.

## ADDED Requirements

### Requirement: Behavior has one home

Every behavior the repository commits to SHALL be stated as a requirement in
exactly one `openspec/specs/<capability>/spec.md`. No document under
`docs/knowledge/data/` SHALL state a requirement or describe behavior a spec
owns; it SHALL link the spec instead. The graph SHALL have no `spec` or
`architecture` document type.

#### Scenario: A graph document needs to describe behavior

- **WHEN** a plan, bug, task, feature, or finding depends on how the system
  behaves
- **THEN** it links the owning requirement under `openspec/specs/` rather than
  restating it

#### Scenario: A document of a retired type is added

- **WHEN** a commit adds a document under `docs/knowledge/data/` with
  `type: spec` or `type: architecture`
- **THEN** `iwe schema validate` fails and names the document

#### Scenario: Behavior has no spec yet

- **WHEN** implemented behavior is described somewhere but no spec states it
- **THEN** it becomes a requirement in the spec whose purpose covers it, or in a
  new spec when none does

### Requirement: Behavior changes go through an OpenSpec change

A change to specified behavior SHALL be planned as an OpenSpec change under
`openspec/changes/`, and its delta SHALL reach `openspec/specs/` only by
archiving that change. An IWE plan SHALL carry no spec content; a plan whose
work changes behavior SHALL link the OpenSpec change that specifies it.

#### Scenario: An IWE plan changes behavior

- **WHEN** a plan's work adds, changes, or removes specified behavior
- **THEN** the plan links the OpenSpec change that carries the delta, and holds
  no requirement or scenario text itself

#### Scenario: A plan changes no behavior

- **WHEN** a plan's work leaves every spec unchanged
- **THEN** the plan links no OpenSpec change

### Requirement: A spec carries its rationale

A spec MAY carry a `## Rationale` section after `## Requirements`. It SHALL hold
only the decisions in force behind the spec's requirements, who made each, and
the alternatives each rejected. It SHALL NOT state behavior that
`## Requirements` does not, nor record how a decision was reached.

#### Scenario: A change is archived

- **WHEN** `openspec archive` merges a delta into a spec that has a
  `## Rationale` section
- **THEN** the section is unchanged by the merge

#### Scenario: A decision is overturned

- **WHEN** a newer decision replaces one recorded in `## Rationale`
- **THEN** the replaced decision is rewritten as an alternative the newer one
  rejected, and nothing in the spec presents it as in force

#### Scenario: Rationale describes behavior

- **WHEN** a rationale paragraph states something the system does
- **THEN** that statement is a requirement or scenario under `## Requirements`,
  and the paragraph keeps only why

### Requirement: Archiving a change keeps rationale current

Archiving an OpenSpec change SHALL fold each decision in its `design.md` that
stays in force after the change into the `## Rationale` of the spec that
decision shapes, with the alternatives it rejected, in the same commit as the
archive.

#### Scenario: A design decision shapes a spec

- **WHEN** a change whose `design.md` decides how a capability behaves is
  archived
- **THEN** that decision and its rejected alternatives appear in the
  capability's `## Rationale` in the archive commit

#### Scenario: A design decision has no lasting effect

- **WHEN** a decision in `design.md` concerns only how the change was carried
  out
- **THEN** it stays in the archived change and no spec gains it

### Requirement: Findings and procedures live outside specs

A measurement or an investigation SHALL be a `type: finding` document at
`docs/knowledge/data/findings/<slug>.md`, linked from the `findings` hub. A
procedure for running or testing something SHALL be a guide under `docs/`
outside `docs/knowledge/`. Neither SHALL be placed in a spec.

#### Scenario: An investigation is recorded

- **WHEN** a session measures host or tool behavior to answer an open question
- **THEN** the measurement, the hypotheses eliminated, and what would settle it
  go in a finding document

#### Scenario: A finding settles a decision

- **WHEN** a finding's closing produces a decision that shapes behavior
- **THEN** the decision goes into the owning spec's `## Rationale` and the
  behavior into its requirements, and the finding links that spec

#### Scenario: A how-to procedure is recorded

- **WHEN** a document explains how to run a build, test, or rehearsal
- **THEN** it is a guide under `docs/`, and links the specs it relies on
