---
type: codebase
description: Workflows, composite actions, Renovate policy, and the pull request template that gate and publish this repository.
source: .github
source_digest: sha256:980ef5c9e8d80637b7e03574a6cad6ec92afbbb489d5674c03f16de005fd8b86
verified:
  by: claude-code/opus-5.5
  at: 2026-09-26T00:00:00Z
stale_after: 2026-12-25
generated:
  by: claude-code/opus-5.5
  at: 2026-09-26T00:00:00Z
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

- `renovate.json` — the self-hosted bot's repository config: automerges GitHub
  Actions updates, pre-commit hook revisions, lock-file maintenance, the
  `agent-desktop` digest (grouped so every copy moves in one PR), and the
  Ansible role pins its custom regex managers extract from `# renovate:`
  comments under `ansible/roles/*/defaults/`, checksum-carrying `dev_tools`
  entries included; runs `scripts/renovate-post-upgrade.sh` after every upgrade
  that touches the listed paths; disables Renovate for the Super-Linter family,
  which `/agentdev:sync-super-linter-tool-versions` moves by hand, and for the
  `ubuntu` base of `docker/ansible/Dockerfile`, which stays at 24.04
- `.agent.metadata.json` — `iwe-map.digest_ignore` masks for runner labels and
  `agent-desktop` digests, so automerged bumps leave map digests unchanged
- `pull_request_template.md` — the verification sections
  [PR verification sections](../architecture/pr-verification-sections.md)
  describes

## How it works

`primary-checks.yml` is the entry workflow; it calls the reusable `reformat.yml`
and `ci.yml`. Three more workflows trigger independently on their own path
filters, `renovate.yml` runs the bot on a schedule and on every push to `main`,
and one is manual. Knowledge validation has its own inner filter so the consumer
IWE seed tests run only when the seed, schemas, or seed test moved. Agent-file
validation includes every source path declared by a codebase map doc, so source
drift cannot skip the staleness gate.

## Depends on

The [Dockerfiles](docker.md) and [playbook](ansible.md) for the image jobs; `uv`
and the [validator](py_packages/validate_agent_files.md) for the check jobs;
`iwe` for the knowledge-base job.

## Invariants & gotchas

- The digest pin Renovate advances lives outside every path the image filter
  watches; that is what makes its automerge safe. Workflow container jobs pin
  the same digest and move with it.
- Actions are pinned to exact versions and audited by `zizmor` in pre-commit.
- The agent-file workflow's source filter stays aligned with codebase map
  frontmatter.
- `renovate.json` is itself validated, by a pre-commit hook and by
  `validate-renovate-config.yml`, both running the validator with `--no-global`
  so it applies the repository schema rather than the self-hosted one, at the
  hook's Renovate rev the bot also runs — see
  [Renovate config validation](../architecture/renovate-config-validation.md).
- The post-upgrade script's behavior and failure policy are
  [Renovate post-upgrade](../architecture/renovate-post-upgrade.md).

## Key references

Verified anchor points (line numbers as of 2026-09-26):

- `.github/renovate.json:5-21` — `postUpgradeTasks`
- `.github/renovate.json:22-27` — lock-file maintenance automerge
- `.github/renovate.json:32-38` — Actions automerge
- `.github/renovate.json:39-47` — `agent-desktop` digest group and automerge
- `.github/renovate.json:48-54` — Dockerfile `ubuntu` base disabled
- `.github/renovate.json:55-61` — pre-commit hook revisions automerged
- `.github/renovate.json:62-84` — Super-Linter family disabled
- `.github/renovate.json:85-101` — role dependency pins grouped and automerged,
  with `astral-sh/uv` grouped across both places it is pinned
- `.github/renovate.json:103-140` — the custom managers: post-upgrade script's
  devcontainer CLI, `dev_tools` versions, role version pins, commit pins
- `.github/.agent.metadata.json` — runner-label and image-digest masks
- `.github/workflows/validate-knowledge-base.yml:69-109` — seed filter and
  standalone seed validation
