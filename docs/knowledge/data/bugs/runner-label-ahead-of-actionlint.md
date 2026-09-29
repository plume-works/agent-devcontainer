---
type: bug
description: Renovate proposes the ubuntu-26.04 GitHub-hosted runner label before any actionlint release knows it, so the post-upgrade script and Super-Linter both fail the runner bump.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-29T12:00:00Z
sources:
- resource: https://github.com/plume-works/agent-devcontainer/pull/208
- resource: .github/renovate.json
- resource: .pre-commit-config.yaml
- resource: .github/workflows/ai-responder.yml
- resource: .github/workflows/reformat.yml
- resource: scripts/renovate-post-upgrade.sh
- resource: .github/actionlint.yml
- resource: .agents/plugins/agentdev/bin/super-linter-env.sh
stage: done
---

# Bug: Runner label bump ahead of actionlint

## Symptom

Renovate's `github-actions` manager, through the `github-runner` datasource,
proposes `ubuntu-24.04` → `ubuntu-26.04` for every literal `runs-on` label.
actionlint rejects the new label with `label "ubuntu-26.04" is unknown`
(`runner-label`), so the pull request fails twice:

- `renovate/artifacts` — the post-upgrade script's pre-commit pass fails on the
  actionlint hook, and Renovate reports
  `Command failed: scripts/renovate-post-upgrade.sh`.
- `Reformat code / Super-Linter` — the `GITHUB_ACTIONS` linter fails on the same
  four lines.

The pull request can never go green on its own, and Renovate keeps it open.

## Reproduction

Pull request #208 (`renovate/ubuntu-26.x`) edits
`.github/workflows/ai-responder.yml` and `.github/workflows/reformat.yml`.
Running
`pre-commit run actionlint --files .github/workflows/ai-responder.yml .github/workflows/reformat.yml`
on that branch reports the unknown label at `ai-responder.yml:120`, `:371`,
`:518` and `reformat.yml:192`.

## Root cause

actionlint validates GitHub-hosted runner labels against a list compiled into
the binary. v1.7.12, the newest release and the version the Super-Linter parity
contract pins for both the pre-commit hook and Super-Linter, predates
`ubuntu-26.04`. Renovate learns about runner images from GitHub's runner-images
releases, so it can propose a label before actionlint ships support for it.

Only literal labels are rewritten; the expression-form labels
(`vars.AMD_ONLY == '1' && 'ubuntu-24.04' || …`) are not extracted, so a merged
bump would also leave the workflows on mixed runner releases.

## Fix

`.github/actionlint.yml` declares `ubuntu-26.04` under
`self-hosted-runner.labels`. The pre-commit hook finds it by actionlint's own
discovery, and `super-linter-env.sh` sets `GITHUB_ACTIONS_CONFIG_FILE` to it, so
both lint passes accept the label; any other unknown label, a typo included,
still fails. A label leaves the file once an actionlint release knows it.

The expression-form labels are not extracted by Renovate and are outside this
fix.

## Key references

Verified anchor points (line numbers as of 2026-09-29):

- `.github/workflows/ai-responder.yml:120`, `:371`, `:518` — literal
  `runs-on: ubuntu-24.04` labels Renovate rewrites
- `.github/workflows/ai-responder.yml:428`, `:475` — expression-form labels
  Renovate does not extract
- `.github/workflows/reformat.yml:192` — literal `runs-on: 'ubuntu-24.04'`
- `.github/workflows/reformat.yml:213` — Super-Linter `slim@v8.7.0`
- `.pre-commit-config.yaml:63-66` — actionlint hook at `v1.7.12`
- `.github/actionlint.yml:4-6` — `self-hosted-runner.labels`
- `.agents/plugins/agentdev/bin/super-linter-env.sh:44` —
  `GITHUB_ACTIONS_CONFIG_FILE`
- `.github/renovate.json:48-54` — the Ubuntu rule, which disables only the
  `dockerfile` base image, not runner labels
