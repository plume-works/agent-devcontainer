---
name: template-consume
description: 'Adopt or update the agent-devcontainer template in a consuming repository — a first-time setup walkthrough (full-copy or existing-repo merge) and an update mode that diffs the tracked template paths since the last-consumed commit. Use when asked to adopt this devcontainer/catalog in another project, bootstrap a new repo from this template, or check/pull in upstream template changes. Keywords: use as template, adopt devcontainer, sync template, pull template updates, agentdev template.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---

# Template Consume

Two modes, chosen by what the consuming repository already has:

- **Setup mode** — no `.agentdev-template.json` marker file at the consumer
  repository root. Walk the user through first-time adoption, then write the
  marker file.
- **Update mode** — a marker file exists. Diff the tracked template paths
  between its `consumed_ref` and the template repository's current default
  branch, then apply the changes the user wants and advance the marker.

Detect the mode by checking for `.agentdev-template.json` at the target
repository root before doing anything else.

## The Marker File

`.agentdev-template.json`, at the consumer repository root, tracked in git:

```json
{
  "source_repo": "plume-works/agent-devcontainer",
  "consumed_ref": "<full 40-character commit SHA>",
  "workflow": "A",
  "optional_bundles": ["custom-image", "knowledge-base"],
  "tracked_paths": [
    ".devcontainer/",
    "devcontainer-compose-pins.yml",
    ".mcp.json",
    "..."
  ],
  "last_synced_at": "<ISO 8601 timestamp>"
}
```

| Field              | Meaning                                                                                                                                                                                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `source_repo`      | `owner/name` of the template repository this consumer was built from.                                                                                                                                                                 |
| `consumed_ref`     | The full commit SHA whose template paths this consumer currently reflects. Always the 40-character form — never abbreviated.                                                                                                          |
| `workflow`         | `"A"` (full-copy) or `"B"` (existing-repo merge), from [Setup Mode](#setup-mode) below.                                                                                                                                               |
| `optional_bundles` | Which optional pieces this consumer kept: `"custom-image"` when the Ansible/Docker publishing bundle was retained, `"knowledge-base"` when IWE project memory under `docs/knowledge/` was adopted. Empty array when neither was kept. |
| `tracked_paths`    | The template-owned paths this consumer still wants compared on update — start from [Default Template Surface](#default-template-surface) and prune what setup mode deleted.                                                           |
| `last_synced_at`   | When `consumed_ref` was last advanced.                                                                                                                                                                                                |

`consumed_ref` is what [check-updates.sh](scripts/check-updates.sh) diffs
from; `tracked_paths` is what it diffs. Both must stay accurate — a stale
`tracked_paths` after setup mode deletes a bundle produces false positives
forever after.

## Setup Mode

No marker file. Read [the full consumption guide](references/consumption-guide.md)
before starting — it has the complete step-by-step content for both workflows,
every collision to avoid, and the two Requirement scenarios (a silently
dead `[tool.ruff]` block, a reformatted verbatim capture) that setup must not
recreate.

1. **Ask which workflow applies** (AskUserQuestion, or ask in prose and stop if
   unavailable): Workflow A (a fresh full copy — GitHub "Use this template",
   or a clone into a new repository) or Workflow B (adding the template
   surface to an existing repository that already has its own source, CI, and
   possibly its own `pyproject.toml`/pre-commit config).
2. **Ask the scope questions** the guide's own steps depend on: keep custom-image
   publishing (§3 / Optional custom-image setup)? Keep IWE-based project memory
   under `docs/knowledge/`? Keep the shared `agentdev-agents-auth` credential
   volume default?
3. **Execute the guide's numbered steps** for the chosen workflow using your
   normal file tools — this is an agent-guided walkthrough, not a script. Merge
   rather than overwrite wherever the guide says to (Workflow B step 3
   especially: never replace an existing project manifest, lockfile, or lint
   config without the user's go-ahead).
4. **Run the guide's verification section** before declaring success.
5. **Write the marker file**: resolve the exact commit SHA of the template
   checkout you copied from or merged from (`git rev-parse HEAD` in that
   checkout, or the release/ref the user named), record `workflow`,
   `optional_bundles`, and a `tracked_paths` list pruned to what this consumer
   actually kept, and set `last_synced_at` to now. Commit it with the rest of
   the setup changes.

If the user is running this skill _from inside the template repository itself_
against a different target directory, make that explicit before touching
anything — setup mode's deletions target the _consumer_ copy, never this
repository's own tracked source.

## Update Mode

A marker file exists.

1. Run [check-updates.sh](scripts/check-updates.sh) from the consumer
   repository. It clones the template repository into a scratch directory
   under `./.tmp/`, diffs every path in `tracked_paths` between `consumed_ref`
   and the clone's current default-branch HEAD, and cleans up the clone on
   exit regardless of outcome.

   | RESULT            | Exit | Action                                                                                      |
   | ----------------- | ---- | ------------------------------------------------------------------------------------------- |
   | `UP_TO_DATE`      | `4`  | Report it and stop; nothing to do.                                                          |
   | `CHANGES_FOUND`   | `5`  | Continue to step 2 with the printed `CHANGED_PATHS` list.                                   |
   | `NO_MARKER`       | `3`  | Wrong mode — fall back to [Setup Mode](#setup-mode).                                        |
   | `INVALID_MARKER`  | `7`  | Report the marker is malformed; fix `consumed_ref`/`tracked_paths` by hand or re-run setup. |
   | `CLONE_FAILED`    | `6`  | STOP and report the blocker — check network access and `--repo`/`--repo-url`.               |
   | `PREFLIGHT_ERROR` | `2`  | STOP and report the blocker verbatim.                                                       |
   | `SCRIPT_FAILURE`  | `1`  | STOP and report the blocker verbatim.                                                       |

2. **For each changed path**, inspect the actual upstream diff (the scratch
   clone is gone by the time the script returns, so re-clone or use
   `git log`/`git show` against `https://github.com/<source_repo>` — do not
   guess from the path name alone) and decide with the user whether to pull it
   in. A path this consumer customized (renamed values, pruned an unwanted
   hook, edited a workflow's owner gate) needs a manual merge, not a blind
   overwrite — copying the upstream file verbatim would silently undo the
   consumer's own edits.
3. **Re-run the two silent-drift requirements from the guide** if the changed
   paths touch lint configuration: confirm `.ruff.toml` and `pyproject.toml`
   never both configure ruff, and confirm no formatter change was just pointed
   at a directory holding verbatim third-party captures.
4. **Re-run the PR-template evaluation** if `CHANGED_PATHS` includes
   `.github/pull_request_template.md`: walk the guide's §4 "The pull request
   template" procedure against the consumer's _current_ template (which may
   itself already carry a `.github/pr-description-guidance.md` to preserve), so
   an upstream template change does not silently discard captured guidance or a
   consumer heading.
5. **Advance the marker**: set `consumed_ref` to the upstream SHA the update
   was taken from (not necessarily the latest — the user may stop partway
   through the changed-paths list) and `last_synced_at` to now. Commit the
   applied changes and the marker update together, or in clearly separated
   commits — never leave the marker advanced past what was actually applied.

## Default Template Surface

The paths a fresh Workflow A setup keeps, before any project-specific pruning —
seed `tracked_paths` from this list and remove what setup mode deletes for this
consumer:

```text
.devcontainer/
devcontainer-compose-pins.yml
.mcp.json
AGENTS.md
CLAUDE.md
.claude/
.codex/
pyproject.toml
.pre-commit-config.yaml
.ruff.toml
.clang-format
.ansible-lint.yml
.hadolint.yaml
.shellcheckrc
.markdownlint.yml
.prettierrc.yml
.prettierignore
zizmor.yaml
.editorconfig
.gitignore
.github/
```

Add `ansible/`, `ansible.cfg`, `docker/`, `.dockerignore` only when
`optional_bundles` includes `"custom-image"`. Add `docs/knowledge/` and `.iwe/`
only when it includes `"knowledge-base"`. Never add `.agents/`,
`.claude-plugin/`, `py_packages/`, or `scripts/validate-super-linter-tool-versions.sh`
— those are publisher-only source this guide has the consumer delete during
setup, so they can never be legitimate members of a consumer's `tracked_paths`.

`.github/pr-description-guidance.md` is not in the copied list above: this
repository does not carry it, and it is created only when the guide's §4 capture
step writes a consumer's PR-template extras into it. Add it to `tracked_paths`
the moment capture creates it, so update mode's step 4 preserves it on later
PR-template changes. `template-boundary` classifies it as Customize /
consumer-created.
