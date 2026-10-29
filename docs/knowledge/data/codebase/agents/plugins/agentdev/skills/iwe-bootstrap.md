---
type: codebase
description: The iwe-bootstrap skill — a packaged blank IWE workspace and the fail-closed helper that installs it into a repository root.
source: .agents/plugins/agentdev/skills/iwe-bootstrap
source_digest: sha256:f89298a99aab92baa954f326ea8f7d225c613f3916613d9f31ee2249ce17424a
verified:
  by: claude-code/opus-5.5
  at: 2026-10-29T19:33:18Z
stale_after: 2027-01-27
generated:
  by: claude-code/opus-5.5
  at: 2026-10-29T19:33:18Z
sources:
- id: code
  resource: .agents/plugins/agentdev/skills/iwe-bootstrap
---

# iwe-bootstrap skill

The skill that installs a blank IWE workspace — `.iwe/` plus `docs/knowledge/` —
into one repository root from files it ships, then stops. `assets/` is laid out
as a repository root; `agent-code/bootstrap-iwe.sh` classifies the target,
stages and validates the copy, and moves it into place.

## Public surface

- `agent-code/bootstrap-iwe.sh [--root <dir>]` — prints `ROOT`, optionally
  `RECOVERED_TRANSACTION`, `CONFLICT=<reason>:<path>` lines, and `NEXT_SKILLS`,
  ending `RESULT=` `SUCCESS`, `MISSING_DEPENDENCY` (3), `ALREADY_INITIALIZED`
  (4), `RECONCILIATION_REQUIRED` (5), or `VALIDATION_FAILED` (6)
- `assets/.iwe/` — configuration (`[workspace].path = "docs/knowledge"`) and
  schemas
- `assets/docs/knowledge/` — knowledge instructions, `LICENSE.md`, and the
  starter `data/` graph: hubs, ✏️ product placeholders, `*.example.md`
  documents, and the `fill-product-doc` and `capture-current-architecture`
  onboarding tasks `iwe-setup` closes by key
- `<root>/.iwe-bootstrap.txn/` — the helper's transaction directory, marked by
  an `OWNER` file recording its phase

## How it works

The helper resolves `--root` or the git top level, requires `iwe` on PATH, then
recovers any transaction directory: a `staging` phase is discarded, a
`committing` phase is finished by moving whatever is still staged, a directory
holding nothing or only its first, unrenamed `OWNER.next` counts as `staging`,
and any other directory without its marker is a `foreign-transaction` conflict.
With both managed trees absent it copies `assets/` into the transaction's
`stage/`, runs `iwe schema validate` there, checks that `iwe normalize` on a
second copy changes nothing, records `committing`, and renames `.iwe/` and
`docs/knowledge/` into the root. With either tree present it reports
`ALREADY_INITIALIZED` only when every structural scaffold file — everything
outside the document folders under `data/` — exists, the workspace path is
`docs/knowledge`, and the root validates; anything else is
`RECONCILIATION_REQUIRED` with nothing written.

## Depends on

The [bin helpers](../bin.md)' `result-codes.sh`, `git`, and the `iwe` CLI.
`template-consume` invokes this skill for knowledge initialization.

## Invariants & gotchas

- The scaffold's `.iwe/` files and knowledge instructions must stay byte-equal
  to this repository's own; the [knowledge
  workspace](../../../../docs/knowledge.md) tests enforce it and that every
  asset is tracked.
- Every asset must already be in `iwe normalize` form, or a fresh install fails
  with `VALIDATION_FAILED`.
- The validator does not scan `assets/` for references: the scaffold's
  extension-less IWE links resolve only once installed.
- The helper never deletes or overwrites a path it did not create; the only
  state it removes is its own transaction directory, whose `OWNER` it removes
  last so an interrupted cleanup still reads as owned.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh:14`
  — the declared results
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh:143`
  — `discard_transaction`, cleanup that removes `OWNER` last
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh:157`
  — `transaction_phase`, recognition of owned state
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh:192`
  — interrupted-transaction recovery
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh:233`
  — `required_files`, the completeness set
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh:301`
  — staged validation and the normalize no-op check
- `.agents/plugins/agentdev/skills/iwe-bootstrap/agent-code/bootstrap-iwe.sh:320`
  — the commit phase
- `.agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md:53` — the result table
- `.agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md:26` —
  ownership and import attribution
- `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/backlog/fill-product-doc.md:12`
  — setup task key
- `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/backlog/capture-current-architecture.md:12`
  — architecture task key
