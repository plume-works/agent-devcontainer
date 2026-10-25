---
type: spec
description: How the iwe-bootstrap skill installs a blank IWE workspace from the installed agentdev catalog without overwriting existing knowledge, and stops before onboarding.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-25T15:52:57Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md
- resource: .agents/plugins/agentdev/tests/test_iwe_bootstrap.py
---

# IWE bootstrap

## Purpose

`/agentdev:iwe-bootstrap` installs a blank IWE project-memory workspace into a
repository root from assets shipped with the installed agentdev catalog. Direct
use and full template adoption share it; see [Template
consumption](template-consumption.md) for how adoption composes it.

## Requirements

### Requirement: bootstrap is self-contained in the installed catalog

The `iwe-bootstrap` skill SHALL install a complete blank IWE workspace into an
explicit repository root using only assets shipped with that installed skill. It
SHALL NOT require an agent-devcontainer source checkout or a network fetch.

#### Scenario: a mounted repository has no IWE workspace

- **WHEN** bootstrap runs against a repository whose managed destinations are
  absent
- **THEN** it installs `.iwe/` and `docs/knowledge/`, including the schemas,
  blank graph, knowledge instructions, and license
- **AND** `iwe normalize` is a no-op and `iwe schema validate` succeeds from the
  repository root

### Requirement: bootstrap never overwrites project knowledge

Bootstrap SHALL classify the target before writing. A complete valid workspace
SHALL be an idempotent success; any partial, incompatible, or colliding managed
destination SHALL stop with the conflicting paths and SHALL preserve every
pre-existing byte.

#### Scenario: bootstrap is repeated

- **WHEN** the installed scaffold is already present and schema-valid
- **THEN** bootstrap reports that initialization is already complete and makes
  no filesystem changes

#### Scenario: project knowledge or configuration already exists

- **WHEN** any managed destination exists but does not constitute the complete
  valid scaffold
- **THEN** bootstrap reports that reconciliation is required
- **AND** it neither deletes, replaces, nor merges the existing content

#### Scenario: installation is interrupted

- **WHEN** bootstrap is interrupted while preparing a fresh workspace
- **THEN** every pre-existing path remains unchanged and any incomplete state is
  identifiable as owned by that bootstrap transaction
- **AND** a later invocation can safely remove or complete only that owned state

### Requirement: bootstrap and onboarding are separate operations

Bootstrap SHALL stop after the blank workspace validates. It SHALL NOT run
`iwe-setup`, run `iwe-map`, answer their confirmation gates, or merge repository
CI and pre-commit configuration.

#### Scenario: direct initialization succeeds

- **WHEN** bootstrap creates a workspace for a mounted repository
- **THEN** it reports `iwe-setup` as the next product-onboarding operation and
  `iwe-map` as the subsequent codebase-mapping operation
