---
name: remote-codespace-session
description: Create, safely sync, use, and stop a GitHub Codespace as this repository's remote build and test machine. Use when the project toolchain is absent locally and Docker is unavailable, or when asked to run work through GitHub Codespaces.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Remote Codespace Session

Use this workflow only when the project toolchain cannot run locally and no
Docker daemon is available. With Docker, use
[microvm-sandbox](../microvm-sandbox/SKILL.md). The bundled scripts derive the
remote checkout as `/workspaces/<repository-name>` from `gh repo view`; do not
replace it with a hardcoded local path.

## Prerequisites

- `gh` is authenticated with `repo` and `codespace` scopes.
- `rsync` is installed locally when syncing uncommitted work.
- Run commands from this repository. Scripts store session data in `./.tmp/`.

## Reading a Script's Result

Every bundled script ends its stdout with `RESULT=<NAME>`, and its exit code
matches that name. Branch on the name, not on the number — the numbers are
local to each script. Two results mean the same thing everywhere:

| RESULT                    | Exit | Meaning                                          | Action                                                                                                                                                   |
| ------------------------- | ---- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CODESPACE_SCOPE_MISSING` | `3`  | The `gh` token lacks the `codespace` OAuth scope | **STOP.** Report the blocker verbatim: this needs a token with `repo` + `codespace` scopes. No script in this skill can proceed until it is fixed.       |
| `PREFLIGHT_ERROR`         | `2`  | Bad usage, not a repo, or `gh`/`rsync` unusable  | **STOP.** Report the blocker verbatim. If `gh` is missing or unauthenticated there is no fallback — this skill has no MCP path, so escalation ends here. |
| `SCRIPT_FAILURE`          | `1`  | The script broke                                 | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                   |

The per-script tables below list only what each script adds.

## Workflow

1. Preview the first possible Codespace creation:

   ```bash
   agent-code/codespace-ensure.sh --dry-run
   ```

   If it reports `ACTION=create`, show the user the proposed machine,
   timeouts, retention, and branch, then obtain explicit approval before
   creating the billable resource. `ACTION=reuse` needs no approval.

2. Create or reuse the approved Codespace:

   ```bash
   agent-code/codespace-ensure.sh
   ```

   | RESULT               | Exit | Meaning                                           | Action                                                                                                                          |
   | -------------------- | ---- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
   | `SUCCESS`            | `0`  | Codespace resolved; `ACTION` says reuse or create | Continue to the sync step. Under `--dry-run` nothing was created and no name was recorded.                                      |
   | `CREATE_FAILED`      | `4`  | `gh codespace create` was rejected                | **STOP.** Show the `gh` error — quota, machine type, and branch problems all land here. Do not retry blindly.                   |
   | `STATE_WAIT_TIMEOUT` | `5`  | Created, but never reached `Available` in time    | The name was still recorded. Re-run the script to keep waiting, or check `gh codespace list`; do not create a second Codespace. |
   | `GH_CALL_FAILED`     | `6`  | A `gh codespace list` lookup failed mid-run       | Retry once; if it persists, **STOP** and report it.                                                                             |

3. Sync local work:

   ```bash
   agent-code/codespace-sync.sh
   ```

   A clean local tree is pushed and synced with git. A dirty local tree is
   copied with rsync without `--delete`, then the script removes only
   Git-tracked paths deleted locally; remote-only files remain intact. Keep
   local work as the source of truth once the remote checkout is safe.

   | RESULT                  | Exit | Meaning                                                   | Action                                                                                                                                                |
   | ----------------------- | ---- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
   | `SUCCESS`               | `0`  | Local work is on the Codespace; `ACTION` names the path   | Continue to the exec step.                                                                                                                            |
   | `REMOTE_CHECKOUT_DIRTY` | `4`  | The Codespace checkout has uncommitted or untracked files | **STOP and ask the user.** Overwriting would destroy that work. Have them commit and push it, or discard it, then re-run sync.                        |
   | `REMOTE_COMMITS_ABSENT` | `5`  | The Codespace checkout has commits that are not on origin | **STOP and ask the user.** Push or recover those commits, or explicitly return the remote checkout to an `origin` commit, then re-run sync.           |
   | `REMOTE_SSH_FAILED`     | `6`  | An SSH call to the Codespace failed                       | The Codespace may be stopped or unreachable. Re-run `codespace-ensure.sh` to wake it, then retry sync once; **STOP** if it fails again.               |
   | `RSYNC_FAILED`          | `7`  | `rsync` could not copy the working tree                   | **STOP.** Show the rsync error; nothing partial should be trusted until it is understood.                                                             |
   | `PUSH_REJECTED`         | `8`  | `git push` failed — typically a diverged branch           | Reconcile locally with `/agentdev:update-branch` and re-run sync. Never force-push, and never update the branch ref through a GitHub API or MCP tool. |

4. Run the original command. The exec script `cd`s into the remote workspace
   itself, so pass the command exactly as you would run it locally:

   ```bash
   agent-code/codespace-exec.sh \
     uv run pytest py_packages/validate_agent_files
   ```

   ```bash
   agent-code/codespace-exec.sh bun test
   ```

   Run `uv sync` remotely first if a dependency changed. Re-sync after each
   local edit.

   The script's own exit code reports the wrapper, never the remote command —
   otherwise a test suite exiting `3` would be indistinguishable from
   `CODESPACE_SCOPE_MISSING`. The remote status is data, printed as
   `REMOTE_EXIT_CODE`.

   | RESULT                  | Exit | Meaning                                         | Action                                                                                                                                        |
   | ----------------------- | ---- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
   | `SUCCESS`               | `0`  | The remote command ran and exited `0`           | Use its output as the result of the run.                                                                                                      |
   | `REMOTE_COMMAND_FAILED` | `4`  | The remote command — or the connection — failed | Read `REMOTE_EXIT_CODE` and the command's own output, and treat it exactly as a local failure of that command. Fix the code, re-sync, re-run. |

5. Retrieve an artifact when needed. Generate an SSH config explicitly (do
   not rely on a prior dirty-tree sync), and derive the same workspace path the
   scripts use:

   ```bash
   name="$(<./.tmp/codespace-name)"
   gh codespace ssh -c "$name" --config > ./.tmp/codespace-ssh-config
   host="$(awk '/^Host /{print $2; exit}' ./.tmp/codespace-ssh-config)"
   remote_workspace_dir="/workspaces/$(gh repo view --json name -q .name)"
   rsync -az -e "ssh -F ./.tmp/codespace-ssh-config" \
     "${host}:${remote_workspace_dir}/.tmp/" ./.tmp/remote/
   ```

6. Stop the Codespace when the session ends. Delete it only with explicit user
   direction:

   ```bash
   agent-code/codespace-teardown.sh
   agent-code/codespace-teardown.sh --delete
   ```

   | RESULT               | Exit | Meaning                                               | Action                                                                                                                             |
   | -------------------- | ---- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
   | `SUCCESS`            | `0`  | Stopped (`Shutdown`) or deleted (gone from the list)  | Done. After `--delete` the recorded name and SSH config are removed too.                                                           |
   | `TEARDOWN_FAILED`    | `4`  | The `gh codespace stop`/`delete` call was rejected    | **STOP** and report it: the Codespace is still running and still billing.                                                          |
   | `STATE_WAIT_TIMEOUT` | `5`  | The stop/delete was accepted; only the wait timed out | Do not re-issue it. Confirm with `gh codespace list` and report the state.                                                         |
   | `GH_CALL_FAILED`     | `6`  | A `gh codespace list` lookup failed while waiting     | Same as above: the stop/delete was already accepted. Confirm with `gh codespace list` rather than re-running teardown immediately. |

## Bundled scripts

- [codespace-ensure.sh](agent-code/codespace-ensure.sh) creates or reuses a
  Codespace. Its help describes machine and polling options.
- [codespace-sync.sh](agent-code/codespace-sync.sh) uses the non-destructive sync
  policy above. Both paths exclude `.git` and locally ignored files, and each
  refuses to touch a remote checkout that holds work of its own.
- [codespace-exec.sh](agent-code/codespace-exec.sh) runs one command remotely in
  the workspace directory and reports that command's exit code as
  `REMOTE_EXIT_CODE`. Everything after the script name is forwarded verbatim,
  including `-h`/`--help`, so the script's own help appears only when it is
  called with no arguments at all.
- [codespace-teardown.sh](agent-code/codespace-teardown.sh) stops or deletes the
  recorded Codespace.

Each script's `--help` carries the same result table as the sections above.
