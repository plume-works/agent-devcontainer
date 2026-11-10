# PR description Specification

## Purpose

Defines the structure `pr-gen-description` gives a pull request description:
closed verification with evidence, open handoff items with who can close them,
and no restatement of what CI or another document already records.

## Requirements

### Requirement: verification and handoff are split by tense

A generated pull request description SHALL carry `## Verification`, holding only
closed `- [x]` items each with an `**Evidence:**` child naming what closed it,
and `## Reviewer Handoff`, holding only open `- [ ]` items each with a
`**Closed by:**` child naming the party who can close it. Neither section SHALL
hold the other's box type. Neither SHALL list what an automated check on the
branch covers, nor restate verification another document records, such as a
plan's per-task evidence, which the description links instead. Either section
MAY be empty.

#### Scenario: CI covers every change

- **WHEN** every check of a change is run by CI on the branch and no manual
  verification was done
- **THEN** `## Verification` is empty and no line claims CI is green

#### Scenario: a check needs a rebuilt devcontainer

- **WHEN** a change can be confirmed only by rebuilding the devcontainer
- **THEN** `## Reviewer Handoff` lists it as `- [ ]` with a `**Closed by:**`
  child naming who can rebuild

### Requirement: the skill owns the structure, and the template is a stub

`pr-gen-description` SHALL state its section structure itself and SHALL NOT read
structure from `.github/pull_request_template.md` or `.github/PULL_REQUEST_TEMPLATE/`.
When a repository carries such a template, the skill SHALL report that it was not
consulted. This repository's `.github/pull_request_template.md` SHALL be a stub
that names no sections and points at the skill.

#### Scenario: a consumer keeps its own pull request template

- **WHEN** `pr-gen-description` runs in a repository whose template lists
  sections
- **THEN** the description follows the skill's structure and the skill reports
  the template was not consulted

## Rationale

### Two sections distinguished by tense

A single `## How to Test` mixed states to observe, commands already run, and
instructions to the reader, as pull request 61 showed with four of six items
restating CI. Every pull request here is reviewed by an agent that will not
rebuild a devcontainer, so an unperformable instruction under one heading is
skipped or absorbed into a verdict; `**Closed by:**` naming someone other than
the reviewer keeps it open. The evidence child matches the plan-checkbox
vocabulary, so one rule has one vocabulary. No mechanical gate can reach a pull
request body, which is why the format stays simple enough to hold by hand. No
pull request is opened by hand and `pr-open` passes `--body-file`, so nothing
read the template's structure; a stub that names no sections cannot drift, keeps
GitHub's web textarea non-empty, and points a human at the skill.

Rejected:

- **Rename `## How to Test` to `## How to Verify`.** It leaves past and future in
  one list.
- **Two sections of prose bullets without per-item evidence.** A different
  vocabulary from plans, and a bullet's closure cannot be told from its text.
- **Delete the pull request template.** The web textarea would open blank with
  no pointer to the structure.
- **Symlink the template at the skill.** Nothing reads the template, the
  structure lives inside `SKILL.md`, and the repository tracks no symlinks.
- **The reviewing agent writes the handoff.** The handoff must exist before
  review to guide it.
