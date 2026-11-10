# CI workflows Specification

## Purpose

Defines repository-wide rules for this repository's GitHub Actions workflows:
how they reference their own actions, and why the image build publishes even
when that fails a fork pull request.

## Requirements

### Requirement: same-repository references use the self-repository syntax

Every `uses:` that names an action or reusable workflow in this repository SHALL
start with `$/`, never `./`, and zizmor's `self-repository` audit SHALL stay
enabled. A job SHALL check out the repository only when a step reads the working
tree.

#### Scenario: a step runs after a failed checkout

- **WHEN** a job's checkout step fails and a later `if: always()` step uses
  `$/.github/actions/log-debug-stats`
- **THEN** the action loads from the running commit

#### Scenario: a workflow adds a ./ reference

- **WHEN** a commit adds `uses: ./.github/actions/<name>`
- **THEN** the zizmor hook fails

### Requirement: the image build always publishes

`ci.yml` SHALL push the images it builds without a publish condition, so a
pull request from a fork fails at the push.

#### Scenario: a fork opens a pull request

- **WHEN** a pull request from a fork runs `ci.yml`
- **THEN** the build fails at its first registry push, and a maintainer reviews
  the change on a branch of this repository

## Rationale

### `$/` loads the running commit

`./` resolves against the working directory when the step starts, so it needs a
prior checkout and loads whatever that checkout or a later step left on disk;
`$/` needs no checkout, cannot be swapped at run time, and counts as pinned for a
full-SHA pinning policy. It is not a security fix: the responder jobs run a
commit the pull request controls under either syntax. It needs github.com with
runner v2.336.0 or newer, so a consumer on GitHub Enterprise Server cannot adopt
the workflows unchanged, and actionlint is pinned from the kjanat fork because
upstream rejects `$/`.

Rejected:

- **Keep `./` and disable the audit.** Every local action would depend on a
  checkout, and the pinning policy would be blocked.
- **`owner/repo/path@sha` references.** An action and its caller could not
  change together.

### Fork builds are not made to pass

The image build is CI's first stage, and every later stage, here and in
consumers such as Dr-QP/Dr.QP, runs inside the image it published. A fork run
that publishes nothing would go green having proved only that Dockerfiles
compile. The read-only fork token stays the boundary: no PAT and no
`pull_request_target` reaches the registry from unreviewed code. Fork builds
become worth supporting once a later stage can consume an image the run produced
without a registry write.

Rejected:

- **Gate the pushes and everything downstream on a publish verdict.** The
  desktop image would build on the last published base, the smoke test would run
  the committed pin, and every downstream stage would need its own skip, a second
  CI topology.
