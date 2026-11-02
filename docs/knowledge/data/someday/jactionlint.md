---
type: someday
description: Evaluate replacing both actionlint and zizmor with jactionlint, an actionlint fork whose security rules follow zizmor's audits.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T16:37:47Z
sources:
- resource: https://github.com/jdx/jactionlint
- resource: https://jactionlint.jdx.dev/zizmor-parity
- resource: https://jactionlint.jdx.dev/actionlint
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: .pre-commit-config.yaml
- resource: zizmor.yaml
---

# Replace actionlint and zizmor with jactionlint

GitHub Actions files pass two pinned linters: actionlint, from the
[kjanat/actionlint](https://github.com/kjanat/actionlint) fork, for correctness,
and zizmor for security. [jactionlint](https://github.com/jdx/jactionlint) is
another actionlint fork that covers actionlint's checks and adds a rule for each
zizmor audit, so one binary and one config could replace both hooks.

kjanat/actionlint was chosen as the actionlint successor because it is a drop-in
replacement: same binary name, flags, config file and checks. jactionlint
changes the tool set, so it is evaluated on its own.

## What it would change

- **One hook and one pin** instead of the `actionlint` and `zizmor` entries in
  `dev_tools_pinned_tools` and `.pre-commit-config.yaml`.
- **Config migration.** It reads `.github/actionlint.yml` and honors
  `# zizmor: ignore[...]` comments; the rule settings and file-and-line ignores
  in `zizmor.yaml` would move to `.github/jactionlint.yaml`.
- **Policy rules.** Its default profile adds checks neither current tool runs,
  such as job timeouts and concurrency groups. Adoption means choosing a
  profile, or recording a baseline that fails only on new findings.

## Open questions

- Does it match zizmor on this repository's workflows: the same findings, and no
  audit lost? Its parity page maps zizmor 1.30.1; this repository already runs a
  newer zizmor.
- Which profile fits, and what does the default profile report here?
- Does it follow new zizmor audits fast enough? zizmor is the reference for
  GitHub Actions security, and jactionlint has one maintainer.

## Promotion criteria

Promote to a task when a run of jactionlint over `.github/` reports every
finding the pinned zizmor reports, and the remaining default-profile findings
are either fixed or accepted in a profile or baseline. Keeping actionlint and
zizmor is also a valid outcome, recorded as a decision.
