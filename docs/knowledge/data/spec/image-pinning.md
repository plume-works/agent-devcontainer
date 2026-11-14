---
type: spec
description: How the published ubuntu-ansible, agentdev-base, agentdev-deploy, and agentdev-devcontainer images are tagged after acceptance, and pinned and updated by consumers.
sources:
- resource: devcontainer-compose-pins.yml
- resource: README.md
- resource: .github/renovate.json
- resource: .github/workflows/validate-renovate-config.yml
- resource: .github/workflows/ci.yml
- resource: .github/workflows/primary-checks.yml
- resource: .github/actions/docker/promote/action.yml
- resource: .github/actions/docker/multiarch-merge/action.yml
- resource: opencode-compose-pins.yml
- resource: .github/actions/paths-filter/action.yml
- resource: docker/ansible/Dockerfile
- resource: scripts/ci-cooldown.py
---

# Image pinning

## Requirement: published tags name only tested images

CI SHALL publish `ubuntu-ansible`, `agentdev-base`, `agentdev-deploy`, and
`agentdev-devcontainer` candidates under immutable commit tags and SHALL move
event tags only after native deploy and Dev Container acceptance and the
candidate pre-commit run pass for the same digests, without rebuilding. CI SHALL
NOT move a tag to an image built from an ancestor of the commit it names, which
it reads from the `org.opencontainers.image.revision` label of the image the tag
names; a label naming a commit outside the checkout's history SHALL NOT block
the move. The `ubuntu-ansible` image has no such label, so its tags always move:
[Bug: the promote step can move the `ubuntu-ansible` tags to an older
image](../bugs/ubuntu-ansible-tags-can-move-backwards.md). No Primary checks run
SHALL cancel a run on `main` whose `ci` job has started. On each other ref, a
newer run SHALL cancel the older run for that ref.

### Scenario: every acceptance check passes

- **WHEN** the run's image and runtime checks pass
- **THEN** the event's moving tags name the exact digests that run built and
  tested.

### Scenario: a check fails or the run is cancelled

- **WHEN** any required acceptance job fails or the run is cancelled
- **THEN** every moving tag keeps its previous digest, and only the immutable
  commit tag names the new image family.

### Scenario: a moving tag names a commit outside the history

- **WHEN** a moving tag's image carries a revision label naming a commit the
  checkout does not hold, such as a pull request's earlier merge commit
- **THEN** the run moves the tag to its own tested digest.

### Scenario: pushes to main arrive during a run

- **WHEN** commits land on `main` after a run's `ci` job started and before that
  run completes
- **THEN** that run completes, and the newest waiting run follows it.

## Unknowns

- The exact policy for how often the digest pin should be advanced (on every
  Renovate PR vs. batched) is not written down anywhere found in the code.
