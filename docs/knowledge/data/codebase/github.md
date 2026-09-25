---
type: codebase
description: Workflows, composite actions, Renovate policy, and the pull request template that gate and publish this repository.
source: .github
source_digest: sha256:58f5475aab12dc9cdd8eb5dfb18ec4bb4577918035e097ef3f3fdce8ea47fa15
verified:
  by: claude-code/opus-5.5
  at: 2026-09-25T00:00:00Z
stale_after: 2026-12-24
generated:
  by: claude-code/opus-5.5
  at: 2026-09-25T00:00:00Z
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

- `renovate.json` — automerges GitHub Actions updates, the `agent-desktop`
  digest pin, the Ansible role dependency pins its two custom regex managers
  extract from `# renovate:` comments under `ansible/roles/*/defaults/`;
  disables Renovate for the Super-Linter family, which
  `/agentdev:sync-super-linter-tool-versions` moves by hand, and for the
  `ubuntu` base of `docker/ansible/Dockerfile`, which stays at 24.04
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
- `renovate.json` is itself validated, by a pre-commit hook and by
  `validate-renovate-config.yml`, both running the validator with `--no-global`
  so it applies the repository schema rather than the self-hosted one — the
  split, and why only one side pins Renovate, is
  [Renovate config validation](../architecture/renovate-config-validation.md).

## Key references

Verified anchor points (line numbers as of 2026-09-25):

- `.github/renovate.json:9-15` — Actions automerge
- `.github/renovate.json:16-23` — `agent-desktop` digest automerge
- `.github/renovate.json:24-30` — Dockerfile `ubuntu` base disabled
- `.github/renovate.json:31-53` — Super-Linter family disabled
- `.github/renovate.json:54-70` — role dependency pins grouped and automerged,
  with `astral-sh/uv` grouped across both places it is pinned
- `.github/renovate.json:73-90` — the two custom managers: version pins and
  commit pins
- `.github/workflows/validate-knowledge-base.yml:69-109` — seed filter and
  standalone seed validation
