---
type: codebase
description: Workflows, composite actions, Renovate policy, and the pull request template that gate and publish this repository.
source: .github
source_digest: sha256:67452bd80db66e0e0a3a50303a40ae9083494ce57d020c96c7082a7069f5435e
verified:
  by: claude-code/opus-5
  at: 2026-09-10T02:25:00Z
stale_after: 2026-12-09
generated:
  by: claude-code/opus-5
  at: 2026-09-10T02:25:00Z
sources:
- id: code
  resource: .github
---

# GitHub automation

Everything GitHub runs for the repository: the workflows that check and build,
the composite actions they share, `renovate.json`, and
`pull_request_template.md`.

## Contains

[Workflows](github/workflows.md)

[Composite actions](github/actions.md)

## Public surface

- `renovate.json` — automerges GitHub Actions updates and the `agent-desktop`
  digest pin; disables Renovate for the Super-Linter family, which
  `/agentdev:sync-super-linter-tool-versions` moves by hand
- `pull_request_template.md` — the verification sections
  [PR verification sections](../architecture/pr-verification-sections.md)
  describes

## How it works

`primary-checks.yml` is the entry workflow; it calls the reusable `reformat.yml`
and `ci.yml`. Three more workflows trigger independently on their own path
filters, and one is manual. Knowledge validation has its own inner filter so the
consumer IWE seed tests run only when the seed, schemas, or seed test moved.
Agent-file validation includes every source path declared by a codebase map doc,
so source drift cannot skip the staleness gate.

## Depends on

The [Dockerfiles](docker.md) and [playbook](ansible.md) for the image jobs; `uv`
and the [validator](py_packages/validate_agent_files.md) for the check jobs;
`iwe` for the knowledge-base job.

## Invariants & gotchas

- The digest pin Renovate advances lives outside every path the image filter
  watches; that is what makes its automerge safe.
- Actions are pinned to exact versions and audited by `zizmor` in pre-commit.
- The agent-file workflow's source filter stays aligned with codebase map
  frontmatter.

## Key references

Verified anchor points (line numbers as of 2026-09-06):

- `.github/renovate.json:9-15` — Actions automerge
- `.github/renovate.json:16-23` — `agent-desktop` digest automerge
- `.github/renovate.json:24-40` — Super-Linter family disabled
- `.github/workflows/validate-knowledge-base.yml:69-109` — seed filter and
  standalone seed validation
