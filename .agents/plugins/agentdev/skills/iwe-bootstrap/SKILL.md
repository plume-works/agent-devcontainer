---
name: iwe-bootstrap
description: 'Install a blank IWE project-memory workspace — `.iwe/` plus `docs/knowledge/` with its schemas, starter graph, knowledge instructions, and license — into a repository root from assets shipped with the installed catalog, never overwriting existing knowledge. Use when a repository has no IWE workspace yet and should get one, when asked to initialize, bootstrap, or scaffold project memory or a knowledge base, or when another skill needs a blank workspace before /agentdev:iwe-setup. Keywords: iwe init, bootstrap iwe, knowledge base scaffold, project memory, docs/knowledge.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Bootstrap an IWE workspace

Install the blank workspace this skill carries into one repository, validate
it, and stop. Everything comes from this skill's `assets/`; no source checkout
of another repository and no network fetch is involved. What the scaffold holds
and who maintains it is in [the scaffold reference](references/scaffold.md).

Bootstrap creates `.iwe/` and `docs/knowledge/` and nothing else. It does not
fill the product document, map the codebase, answer onboarding questions, or
add CI workflows, pre-commit hooks, or other repository configuration.

## When to Use This Skill

- A repository should start keeping IWE project memory and has neither `.iwe/`
  nor `docs/knowledge/`
- `/agentdev:template-consume` reaches knowledge-base initialization
- Checking whether a repository already holds a complete IWE workspace

## Safety Rules

1. Never delete, overwrite, or merge an existing `.iwe/` or `docs/knowledge/`.
   The helper refuses before writing; resolving a conflict is the user's
   decision, never a cleanup you make to get the helper to succeed.
2. Never run `/agentdev:iwe-setup` or `/agentdev:iwe-map` from this skill, and
   never answer their questions; report them as next steps.
3. Remove `<root>/.iwe-bootstrap.txn/` only by rerunning the helper, which
   recognizes the state it owns. Never delete it by hand.

## Workflow 1: Resolve the Root

Use the repository root the user names, or the current repository's root. When
the target is a different repository from the one the session is working in,
pass it explicitly. Name the root back to the user before writing.

## Workflow 2: Run the Helper

```bash
agent-code/bootstrap-iwe.py [--root <dir>]
```

Without `--root`, the helper uses `git rev-parse --show-toplevel` from the
current directory. It stages the scaffold in `<root>/.iwe-bootstrap.txn/`, runs
`iwe schema validate` and confirms `iwe normalize` is a no-op there, and only
then moves `.iwe/` and `docs/knowledge/` into place. The last line of stdout is
always `RESULT=<NAME>`.

## Workflow 3: Handle the Result

| RESULT                    | Exit                | Meaning                                                                                                     | Action                                                                                                                                                                                                       |
| ------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `SUCCESS`                 | `0`                 | The scaffold was installed at `ROOT` and validated                                                          | Report the root. When `RECOVERED_TRANSACTION` is printed, say an interrupted run was `discarded` or `completed`. Name `NEXT_SKILLS` as the next operations: `/agentdev:iwe-setup`, then `/agentdev:iwe-map`. |
| `ALREADY_INITIALIZED`     | `4`                 | A complete, valid workspace is already present; nothing changed                                             | Report it. Do not reinstall or refresh anything; onboarding state is whatever the workspace already records.                                                                                                 |
| `RECONCILIATION_REQUIRED` | `5`                 | A managed path exists but is not the complete valid scaffold, or a foreign state blocks it; nothing changed | **STOP.** List each `CONFLICT=<reason>:<path>` and ask the user how to reconcile it. Leaving it unmerged is a valid answer.                                                                                  |
| `MISSING_DEPENDENCY`      | `3`                 | The `iwe` CLI is not on PATH; nothing changed                                                               | **STOP.** Ask the user to install IWE (https://iwe.md/quick-start/), then rerun.                                                                                                                             |
| `VALIDATION_FAILED`       | `6`                 | The staged scaffold failed `iwe schema validate` or is not normalized; nothing changed                      | **STOP.** Report the iwe output from stderr verbatim; the installed catalog's scaffold does not match this `iwe`.                                                                                            |
| `PREFLIGHT_ERROR`         | `2`                 | Bad usage, a root that is not a directory, no repository to default to, or no packaged scaffold             | **STOP.** Report the error verbatim and fix the input before retrying.                                                                                                                                       |
| `SCRIPT_FAILURE`          | `1`                 | The helper broke                                                                                            | **STOP.** Report the blocker verbatim; do not work around it.                                                                                                                                                |
| `SIGNAL_*`                | `129`, `130`, `143` | Interrupted by HUP, INT, or TERM                                                                            | **STOP.** Rerun the helper when the user is ready; it discards or completes the interrupted transaction.                                                                                                     |

`CONFLICT` reasons:

- `missing` — the other managed tree, or a structural file of the scaffold, is
  absent while part of the workspace exists
- `not-a-directory` — `.iwe`, `docs`, or `docs/knowledge` is a file or a
  symbolic link
- `incompatible-config` — `.iwe/config.toml` sets a `[workspace].path` other
  than `docs/knowledge`
- `invalid` — the workspace is complete but fails `iwe schema validate`
- `foreign-transaction` — `.iwe-bootstrap.txn` exists but this helper did not
  create it
- `collision` — finishing an interrupted transaction would land on a path that
  appeared since

A workspace counts as complete when it keeps every scaffold file outside the
document folders under `docs/knowledge/data/`, sets `[workspace].path` to
`docs/knowledge`, and validates. Onboarding rewrites and deletes documents, so
an onboarded workspace stays `ALREADY_INITIALIZED`.

## Completion Criteria

- The helper reported `SUCCESS` or `ALREADY_INITIALIZED` for the named root,
  or the user has the conflicts or blocker it reported
- `iwe schema validate` passes from the root after `SUCCESS`
- `/agentdev:iwe-setup` and `/agentdev:iwe-map` are reported as next steps and
  not run
