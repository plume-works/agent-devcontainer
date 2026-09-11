---
type: codebase
description: 'The eight local composite actions the workflows share: the paths filter, the three Docker build helpers, the uv-based Python setup, the API debug logger, and the AI responder helpers.'
source: .github/actions
source_digest: sha256:143a4998aca87818eb150068a1f9ff7eb076851b1a837fb0146daf955df54cbb
verified:
  by: claude-code/opus-5
  at: 2026-09-11T16:01:00Z
stale_after: 2026-12-10
generated:
  by: claude-code/opus-5
  at: 2026-09-11T16:01:00Z
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
invocation, artifact upload, and the usage-limit check. `ai-review-status`
evaluates the acceptance policy in
[AI review gate](../../spec/ai-review-gate.md) once, without waiting.

## Depends on

`dorny/paths-filter`, the `docker/*` upstream actions, `astral-sh/setup-uv`.

## Invariants & gotchas

- The `image` filter list is the definition of "changes that make the published
  image stale"; the digest pin file is deliberately not in it.
- Callers invoke Python tools through `uv run`; `setup-python-venv` never
  activates the environment.
- `run-claude-responder` uploads the execution file and checks it for a usage
  limit under `always()`, so a failed Claude step still leaves its output
  inspectable and a quota failure is still reported as one.
- The settings it hands Claude Code are the tracked `.claude/settings.json`
  merged with `.claude/settings.local.json` only where that gitignored layer
  exists; a repository publishing no marketplace of its own never has one.

## Key references

Verified anchor points (line numbers as of 2026-09-11):

- `.github/actions/paths-filter/action.yml:30-43` — the `image` filter list
- `.github/actions/paths-filter/action.yml:58-71` — PR vs base-branch modes
- `.github/actions/ai-review-status/action.yml:1-27` — inputs and outputs
- `.github/actions/run-claude-responder/action.yml:5-33` — inputs
- `.github/actions/run-claude-responder/action.yml:106-115` — the optional local
  settings layer
- `.github/actions/run-claude-responder/action.yml:137,145` — `always()` on the
  artifact upload and the usage-limit check
- `.github/actions/docker/multiarch-merge/action.yml:20-29` — outputs
