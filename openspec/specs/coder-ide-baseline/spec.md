# Coder IDE baseline contract Specification

## Purpose

This repository's side of the plume-works/coder-ide-baseline Coder template contract — it ships the agent-start command the template defaults to, and keeps Coder user secrets out of Dev Container lifecycle hooks.

[plume-works/coder-ide-baseline](https://github.com/plume-works/coder-ide-baseline)
is the Coder template that runs this repository as a Dev Container. Its
`template/main.tf` is published to Coder as the template `coder-ide-baseline`.
This spec records this repository's side of the contract between the two. The
template's side, and how to change, validate, and ship a template version, is
[`spec/workspace-template`](https://github.com/plume-works/coder-ide-baseline/blob/main/docs/knowledge/data/spec/workspace-template.md)
in the template repository.

## Requirements

### Requirement: the repository ships the Coder agent-start command

The repository SHALL ship `agentdev-runtime coder start`, the command the
`coder-ide-baseline` template's `agent_start_script` parameter defaults to.
Every step that runs on a Coder agent start SHALL run from it; the repository
SHALL NOT rely on the template running any other command in it.

#### Scenario: a workspace starts on the default parameter

- **WHEN** a `coder-ide-baseline` workspace starts with the default
  `agent_start_script`
- **THEN** `agentdev-runtime coder start` runs in the Dev Container with the
  Coder user secrets in its environment.

#### Scenario: a new agent-start step

- **WHEN** a setup step must run on every Coder agent start
- **THEN** it is added to `agentdev-runtime coder start`, not to the template.

### Requirement: Coder user secrets reach only agent-started processes

Dev Container lifecycle hooks (`postCreateCommand`, `postStartCommand`) run
inside `devcontainer up`, before Coder injects its agent into the container.
They SHALL NOT depend on Coder user secrets or on the agent's environment
(`GITHUB_TOKEN`, `CODER_*`, `GIT_ASKPASS`). Setup that needs them SHALL run from
the agent-start command.

#### Scenario: setup needs a user secret

- **WHEN** a setup step needs `GITHUB_TOKEN` supplied as a Coder user secret
- **THEN** it runs from `agentdev-runtime coder start`, not from post-start.
