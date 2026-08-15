## Purpose

Defines where this project's Python environment lives, how project tools are
invoked without activating it, and what the shared CI provisioning action
guarantees to its callers.

## ADDED Requirements

### Requirement: Project environment lives outside the workspace tree

In the devcontainer the project's Python environment SHALL live at a fixed path
outside the workspace, and the workspace tree SHALL NOT contain a `.venv` entry
pointing at it. The path SHALL NOT encode the workspace folder name: the volume
backing it is already isolated per devcontainer instance, so per-workspace
namespacing inside it is redundant.

#### Scenario: Synced devcontainer has no workspace venv

- **WHEN** the environment sync completes in the devcontainer
- **THEN** no `.venv` entry exists at the workspace root
- **AND** the project environment resolves to the configured out-of-tree path

#### Scenario: Two worktrees do not share an environment

- **WHEN** two worktrees of this repository run their devcontainers concurrently
- **THEN** each resolves the project environment to its own storage
- **AND** syncing one does not modify the other's environment

#### Scenario: Environment survives a container rebuild

- **WHEN** a devcontainer is rebuilt for a workspace that was previously synced
- **THEN** the previously installed packages are still present
- **AND** a subsequent sync performs no reinstallation

### Requirement: A stale workspace venv symlink self-heals

Syncing the environment SHALL remove a `.venv` symlink at the workspace root, so
worktrees created before this change do not retain a link to an environment that
is no longer maintained. Syncing SHALL NOT remove a `.venv` directory, which a
consuming project may legitimately own.

#### Scenario: Leftover symlink is cleared

- **WHEN** the environment is synced in a workspace whose root holds a `.venv` symlink
- **THEN** the symlink is removed
- **AND** the sync completes successfully

#### Scenario: A real in-tree environment is preserved

- **WHEN** the environment is synced in a workspace whose root holds a `.venv` directory
- **THEN** that directory is not deleted

### Requirement: Project tools are invoked without activation

Project tools SHALL be invoked through the project runner rather than by
activating an environment or by relying on tools being present on `PATH`. No
process SHALL be required to export `VIRTUAL_ENV` or prepend an environment's
`bin` directory to `PATH` in order for project tooling to work.

#### Scenario: Tool runs in a shell with no environment activated

- **WHEN** a project tool is invoked through the project runner in a shell where
  `VIRTUAL_ENV` is unset
- **THEN** the tool runs at the version pinned by the lockfile

#### Scenario: Environment variables agree

- **WHEN** a terminal is opened in the devcontainer and an environment is exposed
  to it
- **THEN** the exposed environment path is byte-identical to the configured
  project environment path
- **AND** invoking the project runner emits no environment-mismatch warning

### Requirement: Editor integration targets the project environment directly

Editor settings that require a filesystem path to an interpreter or tool SHALL
reference the project environment's real path. Those settings SHALL NOT depend on
the workspace folder location or on the editor's working directory.

#### Scenario: Interpreter and linter paths resolve after a rebuild

- **WHEN** the workspace is opened in the editor after a container rebuild
- **THEN** the configured interpreter path exists and is executable
- **AND** each configured Ansible tool path exists and is executable

### Requirement: Style checking works without an in-tree environment

The repository style check SHALL resolve its linter through the project runner
when the working tree is a project, and SHALL fall back to an in-tree environment
and then to `PATH` otherwise. It SHALL NOT modify the environment as a side effect
of checking.

#### Scenario: Devcontainer has no in-tree environment

- **WHEN** the style check runs in the devcontainer, where the linter is absent
  from `PATH` and no `.venv` exists
- **THEN** the check runs at the pinned linter version
- **AND** it exits non-zero only on style violations

#### Scenario: Consuming project owns an in-tree environment

- **WHEN** the style check runs in a project that has its own in-tree `.venv`
- **THEN** the check runs using an available linter rather than failing

#### Scenario: Checking does not mutate the environment

- **WHEN** the style check runs against a workspace whose environment is already synced
- **THEN** no packages are installed, upgraded, or removed

### Requirement: CI provisions Python through the CI platform, not the runner

The shared CI provisioning action SHALL obtain its Python interpreter from the CI
platform's setup action, and the project runner SHALL be constrained to that
interpreter rather than resolving or downloading its own. The interpreter version
SHALL be pinned rather than derived from the project's minimum-version constraint.

#### Scenario: No second interpreter is provisioned

- **WHEN** a workflow runs the provisioning action
- **THEN** the interpreter used by the project environment is the one the CI
  platform installed
- **AND** no additional interpreter is downloaded

#### Scenario: Version is pinned

- **WHEN** the project's minimum-version constraint would permit a newer
  interpreter than the pinned one
- **THEN** the pinned interpreter is used

### Requirement: The CI provisioning action does not export an activated environment

The provisioning action SHALL NOT export `VIRTUAL_ENV` or extend `PATH` for
subsequent steps. Callers SHALL invoke project tools through the project runner.
Provisioning SHALL verify the lockfile is current, and SHALL fail at the
provisioning step rather than during a later step when it is not.

#### Scenario: Bare invocation is not supported

- **WHEN** a workflow step invokes a project tool by bare name after the
  provisioning action has run
- **THEN** the tool is not resolved from the project environment

#### Scenario: Lockfile drift fails during provisioning

- **WHEN** the lockfile does not match the project metadata
- **THEN** the provisioning step fails
- **AND** no test or validation step runs

#### Scenario: Later steps do not re-resolve the environment

- **WHEN** a workflow step invokes a project tool after successful provisioning
- **THEN** the step does not modify the provisioned environment
