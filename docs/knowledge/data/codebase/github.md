---
type: codebase
description: Workflows, composite actions, Renovate policy, and the pull request template that gate and publish this repository.
source: .github
source_digest: sha256:154d947739c7cef7e2d37a1800f3c58eefe0935154cd7d1dd2f58f85fd8e0c99
verified:
  by: claude-code/opus-5
  at: 2026-09-23T00:00:00Z
stale_after: 2026-12-22
generated:
  by: claude-code/opus-5
  at: 2026-09-23T00:00:00Z
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
  extract from `# renovate:` comments under `ansible/roles/*/defaults/`, and the
  apt pins two more managers extract from `ansible/roles/*/vars/apt_pins_*.yml`
  as `deb` dependencies; disables Renovate for the Super-Linter family, which
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
- Each apt pin file's `registryUrls` must list exactly the repositories its role
  enables, and agree with `ROLE_REPOS` in `scripts/apt-pins-refresh.py`;
  disagreement makes the bot and the script revert each other.
- `renovate.json` is itself validated, by a pre-commit hook and by
  `validate-renovate-config.yml`, both running the validator with `--no-global`
  so it applies the repository schema rather than the self-hosted one.

## Key references

Verified anchor points (line numbers as of 2026-09-22):

- `.github/renovate.json:9-15` — Actions automerge
- `.github/renovate.json:16-23` — `agent-desktop` digest automerge
- `.github/renovate.json:24-46` — Super-Linter family disabled
- `.github/renovate.json:47-63` — role dependency pins grouped and automerged,
  with `astral-sh/uv` grouped across both places it is pinned
- `.github/renovate.json:64-221` — the per-role apt `registryUrls` rules and the
  batched, scheduled `ansible apt pins` group
- `.github/renovate.json:222-267` — the four custom managers: version pins,
  commit pins, and one `deb` manager per architecture
- `.github/renovate.json:268-271` — `vulnerabilityAlerts` resetting the schedule
- `.github/workflows/validate-knowledge-base.yml:69-109` — seed filter and
  standalone seed validation
