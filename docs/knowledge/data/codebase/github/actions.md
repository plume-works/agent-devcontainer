---
type: codebase
description: 'The eight local composite actions the workflows share: the paths filter, the three Docker build helpers, the uv-based Python setup, the API debug logger, and the AI responder helpers.'
source: .github/actions
source_digest: sha256:183db93e10b2a6f2d9c3c1714a32aeecd4f564c6cae1b9b06c5ec51ca19008b4
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: .github/actions
---

# Composite actions

Local `using: composite` actions, referenced as `./.github/actions/<name>`.

## Public surface

| Action                     | Inputs                                                                  | Outputs / effect                                                    |
| -------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `paths-filter`             | `event-name`, `base-branch`, `extra-filter`                             | `pass` — whether the `image` filter or an extra filter matched      |
| `docker/build-push-action` | context, file, image, arch, registry creds, build args, `export-digest` | builds and pushes one arch; emits `digest`                          |
| `docker/metadata-action`   | images, arch, prefix                                                    | tags, labels, version JSON                                          |
| `docker/multiarch-merge`   | image, future tag, registry creds                                       | merges per-arch digests; emits `image`, `digest`, `image_pinned`    |
| `setup-python-venv`        | `python-version`                                                        | installs uv and syncs the project; the environment is not activated |
| `log-debug-stats`          | `github-token`                                                          | prints API rate/debug statistics for the job                        |
| `ai-review-status`         | `pr-number`, `github-token`, `trusted-bot-actors`                       | `found`, `reason` — whether an accepted AI review is present        |
| `run-claude-responder`     | tokens, prompt, comment metadata, PR number, artifact name              | runs Claude Code and uploads the responder artifact                 |

## How it works

`paths-filter` builds a filters YAML with a fixed `image` list
(`.devcontainer/**`, `.github/actions/**`, `ansible/**`, `ansible.cfg`,
`docker/**`, `scripts/**`, `.agents/plugins/**`, `.claude-plugin/**`,
`py_packages/validate_agent_files/**`) plus caller-supplied extras, then runs
`dorny/paths-filter` against the PR or a base branch. The Docker trio wraps
`docker/build-push-action`, `docker/metadata-action`, and a manifest merge so
`ci.yml` stays declarative. `run-claude-responder` holds the Claude Code
invocation and artifact upload. `ai-review-status` evaluates the acceptance
policy in [AI review gate](../../spec/ai-review-gate.md) once, without waiting.

## Depends on

`dorny/paths-filter`, the `docker/*` upstream actions, `astral-sh/setup-uv`.

## Invariants & gotchas

- The `image` filter list is the definition of "changes that make the published
  image stale"; the digest pin file is deliberately not in it.
- Callers invoke Python tools through `uv run`; `setup-python-venv` never
  activates the environment.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `.github/actions/paths-filter/action.yml:30-43` — the `image` filter list
- `.github/actions/paths-filter/action.yml:58-71` — PR vs base-branch modes
- `.github/actions/ai-review-status/action.yml:1-27` — inputs and outputs
- `.github/actions/run-claude-responder/action.yml:5-33` — inputs
- `.github/actions/docker/multiarch-merge/action.yml:20-29` — outputs
