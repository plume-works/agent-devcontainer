---
type: plan
created: 2026-09-05
description: Use a fixed Xpra container port and let VS Code resolve local forwarding conflicts.
generated:
  by: codex/gpt-6
  at: 2026-09-06T04:26:49Z
sources:
- resource: docker/desktop/start-xpra.sh
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/docker-compose.yml
- resource: https://github.com/devcontainers/spec/blob/main/docs/specs/devcontainerjson-reference.md
---

# Use VS Code port forwarding for Xpra

## Context

Xpra currently derives its container port from `DEVCONTAINER_ID`, while the
devcontainer configuration requests forwarding for `14500-14599`. The
[image runtime interface](../codebase/api-image-runtime.md) describes that
behavior. Separate devcontainers have separate network namespaces, so each can
listen on the same internal port. The [Dev Container
specification](https://github.com/devcontainers/spec/blob/main/docs/specs/devcontainerjson-reference.md#port-attributes)
defaults `requireLocalPort` to false: forwarding may select another local port
when the preferred one is unavailable.

## Approach

Use container port `14500` by default and declare it explicitly in
`forwardPorts`. VS Code owns local port allocation; developers open the Xpra
HTML5 entry in its Ports panel. Retain `--port` for an explicit container-port
override. Remove the ID hash: it is unnecessary for isolated containers and
cannot guarantee uniqueness across its 100 possible results. Retain explicit
forwarding so availability does not depend on process auto-detection.

The startup script is copied into the image. Adoption must pair the new
forwarding configuration with an image containing the updated script, following
the existing [image pinning contract](../spec/image-pinning.md). Reopening a
container on its old digest does not update `/start-xpra.sh`.

## Implementation Steps

### Task 1: Make the Xpra default independent of container identity

**Files:** Modify: `docker/desktop/start-xpra.sh`,
`docker/desktop/agent-desktop.Dockerfile`

- [x] Retain `PORT=14500` and the `--port` argument; remove the hash block and
  both `PORT_EXPLICIT` assignments, and update the usage text to state the fixed
  default. Preserve bind-host, display, rendering, and lifecycle behavior.
  - **Evidence:** 2026-09-05 disposable-container runtime check on display :199:
    unset, alpha, and beta IDs bound 127.0.0.1:14500; an explicit --port 14600
    with an ID bound 127.0.0.1:14600. All four startup/stop cycles passed.
    `bash -n`, `shellcheck`, and changed-file pre-commit checks passed.
- [x] Describe the startup URL as the container address and direct browser users
  to the forwarded address in VS Code's Ports panel.
  - **Evidence:** The 2026-09-05 four-case runtime check displayed the container
    address and Ports panel instruction in every startup; pre-commit passed.
- [x] Remove the Dockerfile's derived-port claim while retaining `EXPOSE 14500`.
  - **Evidence:** 2026-09-05 source review confirmed EXPOSE 14500 and the fixed
    default comment; changed-file pre-commit, including hadolint, passed.

### Task 2: Forward the fixed container port

**Files:** Modify: `.devcontainer/devcontainer.json`

- [x] Replace the derived-port comment and range configuration with this exact
  configuration fragment, retaining the default `requireLocalPort: false` by
  omission:
  - **Evidence:** 2026-09-05 exact-fragment assertions passed for forwardPorts,
    label, silent forwarding, and omitted requireLocalPort; changed-file
    pre-commit checks passed.

``` json
"forwardPorts": [14500],
"portsAttributes": {
  "14500": {
    "label": "Xpra HTML5",
    "onAutoForward": "silent"
  }
}
```

### Task 3: Align access instructions and project memory

**Files:** Modify: `README.md`,
`docs/knowledge/data/architecture/module-layout.md`,
`docs/knowledge/data/codebase/docker.md`,
`docs/knowledge/data/codebase/api-image-runtime.md`,
`docs/knowledge/data/codebase/devcontainer.md`

- [x] Update the README's Xpra access instructions: fixed internal port,
  possibly different local address in the Ports panel, retained `--port`
  override requiring forwarding of the selected port, and adoption of an image
  containing the changed script before relying on the new configuration.
  - **Evidence:** Commit on branch `ws2` rewriting README's "Reaching the Xpra
    desktop" section with all four points; changed-file pre-commit, including
    prettier, passed.
- [x] Remove the architecture document's obsolete port-derivation detail and
  refresh the affected codebase maps through `agentdev:iwe-map`, including their
  source digests and verified anchors.
  - **Evidence:** Commit on branch `ws2` updating `module-layout.md` and
    refreshing `docker.md`, `devcontainer.md`, and `api-image-runtime.md`;
    `stale-map-docs.sh` reports all three FRESH, `iwe schema validate` and
    changed-file pre-commit checks passed.

### Task 4: Verify concurrent forwarded desktops

**Files:** Modify: this plan's task evidence and Verification results only.

Closed by: a maintainer with two VS Code devcontainer windows and browser
access.

- [x] Complete the two-container check below using the updated script and
  configuration in both containers. Record the image identity, internal and
  local addresses, and successful connections to distinct desktops.
  - **Evidence:** On 2026-09-06, two VS Code devcontainers using pinned image
    digest `5001a1148a8d5f9e5fc0dedbaad26b4536109d7a421d5a54350c6b7d8e901e07`
    each ran the installed updated script on `127.0.0.1:14500`; their Ports
    panels forwarded them to `localhost:14500` and `localhost:14501`, and the
    maintainer successfully used both distinct desktops in the browser.

## Spec changes

Create [Xpra port forwarding](../spec/xpra-port-forwarding.md) during Ship and
include it in the spec hub. Existing specs remain unchanged. The new spec
captures the changed default and preserved explicit-port contract:

``` markdown
## ADDED Requirements

### Requirement: Xpra has a fixed default container port

The startup script SHALL use TCP port 14500 by default, independently of
DEVCONTAINER_ID, and SHALL honor an explicit --port argument.

#### Scenario: default startup

- WHEN Xpra starts without --port, with DEVCONTAINER_ID either unset or set
- THEN it listens on container port 14500.

#### Scenario: explicit override

- WHEN Xpra starts with --port 14600 and DEVCONTAINER_ID is set
- THEN it listens on container port 14600.

### Requirement: devcontainer forwarding permits local remapping

The default devcontainer configuration SHALL explicitly forward container port
14500, label it Xpra HTML5, use silent forwarding, and permit a different local
port when the preferred port is unavailable. Browser access instructions SHALL
direct users to the actual forwarded address in VS Code's Ports panel.

#### Scenario: concurrent devcontainers

- WHEN two isolated devcontainers run Xpra on port 14500 and both are opened
  in VS Code on the same client machine
- THEN both desktops are accessible through their respective forwarded local
  addresses, without requiring distinct container ports.
```

## Verification

- Run `bash -n docker/desktop/start-xpra.sh` and
  `shellcheck docker/desktop/start-xpra.sh`; run the normal pre-commit checks
  for changed files.
- In a disposable container with the edited script, run it with
  `DEVCONTAINER_ID` unset, then with two different nonempty IDs. Confirm each
  default startup binds `127.0.0.1:14500`; stop between runs. Confirm an
  explicit `--port 14600` with an ID set binds `127.0.0.1:14600`. Use an unused
  display and do not stop the developer's existing desktop.
- For Task 4, use two isolated devcontainers built from an image containing the
  updated script and the new forwarding configuration. Confirm each installed
  `/start-xpra.sh` matches the edited source. Open the Xpra HTML5 entry in both
  Ports panels; confirm distinct local addresses reach distinct desktops and
  that HTML5/WebSocket interaction works in both. The remapped local port need
  not be exactly 14501. Keep the checkbox open until this browser check is
  performed; a listener or HTTP response alone is insufficient.
- Run `iwe normalize` and `iwe schema validate` after updating project memory.

## Verification results

On 2026-09-06, two VS Code devcontainers built from pinned `agent-desktop`
digest `5001a1148a8d5f9e5fc0dedbaad26b4536109d7a421d5a54350c6b7d8e901e07` ran
the updated installed `/start-xpra.sh`. Both Xpra servers listened on their
isolated containers' `127.0.0.1:14500`; VS Code forwarded them to
`localhost:14500` and `localhost:14501`. The maintainer opened and interacted
with both distinct desktops successfully.

## Out of scope

- Removing `DEVCONTAINER_ID` from the container environment or changing other
  services' forwarding configuration.
- Supporting multiple Xpra servers in one network namespace through automatic
  server-port allocation, or adding Docker host-port publication.
- Changing image publishing or digest-update policy, Xpra authentication,
  rendering, bind-host defaults, or startup/stop behavior.

## Key references

Verified anchor points (line numbers as of 2026-09-06):

- `docker/desktop/start-xpra.sh:7` — default port
- `docker/desktop/start-xpra.sh:22` — port usage text
- `docker/desktop/start-xpra.sh:152` — --port parsing
- `docker/desktop/start-xpra.sh:224` — printed client URL
- `docker/desktop/start-xpra.sh:231` — Xpra TCP bind argument
- `docker/desktop/agent-desktop.Dockerfile:76` — startup script copied into
  image
- `docker/desktop/agent-desktop.Dockerfile:78` — exposed-port documentation
- `.devcontainer/devcontainer.json:51` — forwarding configuration
- `.devcontainer/docker-compose.yml:53` — devcontainer service
- `.devcontainer/scripts/postStartCommand.sh:20` — background startup entry
  point
- `devcontainer-compose-pins.yml:14` — image digest override
- `README.md:213` — Xpra desktop access instructions
- `docs/knowledge/data/architecture/module-layout.md:89` — port-derivation
  detail
- `docs/knowledge/data/codebase/docker.md:46` — startup-script map
- `docs/knowledge/data/codebase/api-image-runtime.md:44` — ID-to-port contract
- `docs/knowledge/data/codebase/devcontainer.md:36` — forwarding public surface
