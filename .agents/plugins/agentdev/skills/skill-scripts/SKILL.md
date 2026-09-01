---
name: skill-scripts
description: "Write and document a skill's bundled scripts so their outcome is readable by both a shell caller and an agent — a shared exit-code vocabulary, a RESULT= enum line on stdout, and the shared result-codes.sh helpers. Use when adding or editing a script under a skill's scripts/ directory, choosing or renumbering its exit codes, deciding what it prints, or wiring a SKILL.md step to branch on a script's outcome. Keywords: exit code, RESULT, quit_by_code, result-codes.sh, script output contract."
---

# Skill Script Result Contract

A bundled script has two callers with different needs. A shell or test caller
branches on `$?` and needs numeric codes. An agent reads the tool result and
needs a self-describing outcome. Serve both: **keep the exit code, and name it
on stdout.**

Apply this to every script under a skill's `scripts/` directory.

## The Contract

1. **stdout carries the script's product**: the `KEY=value` contract lines, the
   verbatim output of a wrapped command where that output is the point (a
   `git push` transcript, a `git log` excerpt), and any delimiters that frame
   it (`== Commit Log ==`). Everything the script says in its own voice — progress
   narration (`Fetching origin...`), explanations, diagnostics, remediation
   instructions, errors — goes to stderr. When converting a script, move any
   such line that is currently on stdout. `--help` is the exception that proves
   it: requested help text is the run's product, so it goes to stdout, while
   usage printed _because_ an argument was wrong is a diagnostic and goes to
   stderr.
2. **The last line of stdout is always `RESULT=<NAME>`**, on every path
   including success, help, and crashes — and it is the _only_ `RESULT=` line
   the run emits.
3. **The exit code matches the RESULT**, and stays a stable part of the
   script's interface.

## Reserved Codes

| Code  | Name              | Meaning                                                                                                                                                                                                                                                                                              |
| ----- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0`   | `SUCCESS`         | The script did what it was asked.                                                                                                                                                                                                                                                                    |
| `1`   | `SCRIPT_FAILURE`  | The script broke. **Never give `1` a workflow meaning** — `set -e` and unhandled errors produce it, so a deliberate `1` is indistinguishable from a crash. Deliberately reporting a breakage _as_ a breakage (`quit_by_code 1` when a delegate returns something impossible) is the one correct use. |
| `2`   | `PREFLIGHT_ERROR` | Bad usage, or the environment cannot support the operation at all: not a repo, detached HEAD, missing required argument.                                                                                                                                                                             |
| `3`+  | script-specific   | Outcomes the caller must branch on. Number them in the order the workflow meets them and stay at or below `125`.                                                                                                                                                                                     |
| `129` | `SIGNAL_HUP`      | The process received HUP (`128 + 1`). The result is emitted before the signal is re-raised.                                                                                                                                                                                                          |
| `130` | `SIGNAL_INT`      | The process received INT (`128 + 2`). The result is emitted before the signal is re-raised.                                                                                                                                                                                                          |
| `143` | `SIGNAL_TERM`     | The process received TERM (`128 + 15`). The result is emitted before the signal is re-raised.                                                                                                                                                                                                        |

Codes `126`, `127`, and `128+N` are shell-reserved. The shared implementation uses
the conventional `129`, `130`, and `143` statuses only for HUP, INT, and TERM;
never override them with workflow meanings.

## Numbers Are Local, Names Are Shared

Do not try to make one number mean one thing across every skill — `3` is
already "no PR found" in one script and "already up to date" in another, and
forcing a global numbering makes each script's own table arbitrary.

Share the **names** instead. When two scripts hit the same situation, give it
the same `RESULT` name even if the numbers differ: `PROTECTED_BRANCH`,
`GH_UNAVAILABLE`, `ALREADY_UP_TO_DATE`, `PUSH_REJECTED`. That is the whole
reason the string exists — it is unambiguous where a reused number is not.

Name the **outcome**, not the remedy: `NO_PR_FOUND`, not `CREATE_PR_NEXT`. The
SKILL.md table decides the remedy; the script only reports what it saw.
Use `SCREAMING_SNAKE_CASE`, and no `RESULT_` prefix — the key already says it.

Reuse a name only for the _same_ situation, never for an overlapping one. One
script may fold several conditions into a single code because it reacts to
them identically — `pr-open` reports a missing `gh`, an unauthenticated `gh`,
and a failed `gh` call all as `GH_UNAVAILABLE`, since each sends it to the same
MCP fallback. A script that must tell those apart does not reuse that name for
a slice of it; it names its own narrower situation (`GH_CALL_FAILED`) so the
name never claims more than the script observed.

## Give a Distinct Code to Anything the Caller Handles Differently

The point of a separate code is a separate reaction. Split a code out when the
workflow's response differs — most importantly, **a failure a fallback can
rescue must not share a code with a hard stop.** If a skill falls back to a
GitHub MCP server when `gh` is unusable, then a missing `gh`, an
unauthenticated `gh`, _and_ a `gh` API call that failed on scope or network all
belong to the fallback code, not to `PREFLIGHT_ERROR`.

Conversely, do not mint a code the caller reacts to identically. Two forms of
the same dead end are one `PREFLIGHT_ERROR` with different stderr text.

Nor should a code duplicate a distinction the payload already carries. When a
run and a job URL both parse successfully and the caller branches on whether
`JOB_ID` was printed, that is one `SUCCESS` with two shapes — the key is the
discriminator. Codes are for outcomes, not for variants of one outcome.

## Implementation

Source [result-codes.sh](../../bin/result-codes.sh) from the plugin's shared
`bin/` directory. Resolve the path from the consuming script's own location so
it works from both a repository checkout and an installed plugin cache. Never
copy or inline the helpers into a skill.

A skill with a `scripts/__common.sh` loads the shared helpers there:

```bash
skill_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${skill_script_dir}/../../../bin/result-codes.sh"
```

A skill whose `scripts/` holds a single standalone script resolves its own
directory and sources the same file directly. Define alongside it the
`print_error` every converted script uses:

```bash
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${script_dir}/../../../bin/result-codes.sh"
```

The ShellCheck directive acknowledges that the source path is resolved
dynamically at runtime; lint the shared file separately with the other plugin
shell scripts.

In a script that has `__common.sh`, source that file as usual. Declare the
script-specific codes immediately after all shared helpers have loaded, then
call `quit_by_code` on every terminal path:

```bash
source "${script_dir}/__common.sh"

RESULT_CODES+=("3=NO_PR_FOUND" "4=MULTIPLE_PRS" "5=PROTECTED_BRANCH" "6=GH_UNAVAILABLE")

[[ $# -ge 2 ]] || { print_error "Missing value for --branch"; quit_by_code 2; }
...
printf 'PR_FOUND=false\n'
quit_by_code 3
```

`quit_by_code 0` replaces a bare `exit 0`, including at the end of the happy
path and after `--help`. An uncaught failure still prints
`RESULT=SCRIPT_FAILURE` through the `EXIT` trap, so a reader never sees a run
with no verdict.

The shared implementation installs the exit and signal traps:

```bash
trap report_unhandled_exit EXIT
trap 'report_signal HUP 129' HUP
trap 'report_signal INT 130' INT
trap 'report_signal TERM 143' TERM
```

Do not override these traps in a consuming script. Without them, Bash can enter
the `EXIT` trap after HUP, INT, or TERM with the status of the previous successful
command; the process then terminates with `128 + signal` while printing
`RESULT=SUCCESS`. `report_signal` emits the matching signal result, restores
that signal's default action, and re-raises it. A shell caller observes status
`129`, `130`, or `143`, and the operating system still records genuine signal
termination rather than a normal `exit` with the same number. The later
`EXIT` trap sees `result_emitted=1` and does not print a second result.

**Only a top-level path may call `quit_by_code`.** A helper that runs inside
`$( )` cannot: its `RESULT` line is captured into the variable instead of
reaching stdout, and the script then dies through `set -e` and re-emits a
_different_ verdict from the trap. Substitution helpers `return 1`; the caller
decides:

```bash
owner_repo="$(resolve_owner_repo)" || quit_by_code 6
```

## Guard External Commands and Validate Their Products

**Wrap every tool call whose own status could be mistaken for yours.** An
external command may return a number assigned to a different script outcome; if
that status escapes through `set -e`, the script can report a confident, wrong
result. Capture the status, decide what it means, and `quit_by_code` a code you declared.
Keep the tool's stderr visible when it explains the failure:

```bash
if ! git fetch "${remote_name}"; then
  print_error "Failed to fetch remote '${remote_name}'."
  quit_by_code 6  # FETCH_FAILED
fi
```

A successful external call validates only what it actually did. Fetching a
reachable remote does not prove a caller-supplied branch exists. Resolve refs,
ranges, paths, IDs, and similar inputs explicitly before passing them to a
later command whose failure would escape through `set -e`:

```bash
base_ref="${remote_name}/${base_branch}"
if ! git rev-parse --verify --quiet "${base_ref}^{commit}" >/dev/null; then
  print_error "Base branch '${base_ref}' does not exist."
  quit_by_code 2
fi

merge_base="$(git merge-base HEAD "${base_ref}")"
```

Classify the two failures separately: an invalid caller-supplied identifier is
a preflight error, while an attempted routine operation that the caller may
handle differently gets its own declared result such as `FETCH_FAILED`.
`UNKNOWN_CODE_<n>` in a real run is a bug report against the script, not a
reason to widen the table.

## Wrapping a Foreign Exit Status

When a script runs someone else's command — over SSH, in a container, through a
remote shell — that command's exit status cannot also be the script's. Sharing
one number recreates the exact ambiguity this contract removes: a remote test
suite exiting `3` would be indistinguishable from the wrapper's own code `3`.

Report the wrapper's own outcome, and demote the foreign status to a payload
key:

```text
REMOTE_EXIT_CODE=5
RESULT=REMOTE_COMMAND_FAILED
```

The foreign command also owns arbitrary stdout and may omit its final newline.
When its output streams directly to the wrapper's stdout, establish a line
boundary before printing metadata; otherwise `printf foo` becomes
`fooREMOTE_EXIT_CODE=0`, which is not a parseable key-value line:

```bash
status=0
run_remote_command || status=$?

printf '\nREMOTE_EXIT_CODE=%s\n' "${status}"
if [[ "${status}" -ne 0 ]]; then
  quit_by_code 4  # REMOTE_COMMAND_FAILED
fi
quit_by_code 0
```

The unconditional separator may produce a blank line when the foreign output
was already newline-terminated; preserving a parseable contract is more
important than suppressing that harmless whitespace.

Nothing is lost — the exact status is still there for a caller that needs it
(`pytest` 1 vs 5), and `&&` chaining still short-circuits. Say so in `--help`,
since it changes the script's shell-level contract.

## Delegating to Another Script

When a script hands the rest of its work to a sibling script, **align the two
code tables and `exec`**. The delegate then owns the process, and its `RESULT`
line is the run's one verdict:

```bash
exec "${merge_script}" --message "..." "${base_ref}"
```

This requires the shared situations to carry the same number _and_ the same
name in both scripts — which is the natural outcome of the naming rule above.
Reach for `exec` first; it removes the translation layer entirely, and because
`exec` replaces the process it also discards the caller's `EXIT` trap, so no
second `RESULT` line can appear.

Guard the handoff, since a failed `exec` is the one case the discarded trap
would have covered:

```bash
[[ -x "${merge_script}" ]] || { print_error "Merge helper not executable: ${merge_script}"; quit_by_code 1; }
```

Map explicitly only when the tables genuinely cannot align, and then run the
delegate as a call, translate its status, and make sure the delegate's own
`RESULT` line does not reach stdout — two `RESULT=` lines is worse than none,
since a reader takes the last one. Send an unrecognized delegate status to
`quit_by_code 1`.

## Document It Twice

**In the script's `--help`**, add — or replace an existing `Exit codes:` block
with — a paired table, and list `RESULT` first under the output heading. A
script that emits no keys at all heads that section `Output:` and describes the
shape of what it prints instead:

```text
Output (key=value lines):
  RESULT, HEAD_BRANCH, PR_FOUND
  On a match also: PR_NUMBER, PR_URL, PR_STATE, PR_IS_DRAFT, PR_BASE, PR_TITLE

Results (RESULT / exit code):
  SUCCESS           0  Exactly one matching pull request was found
  NO_PR_FOUND       3  No matching pull request exists
  MULTIPLE_PRS      4  Multiple matching pull requests exist
  PROTECTED_BRANCH  5  Branch is a protected default branch
  GH_UNAVAILABLE    6  gh is missing, unauthenticated, or its API call failed
  PREFLIGHT_ERROR   2  Usage or preflight error (not a repo, detached HEAD)
  SCRIPT_FAILURE    1  Unhandled error
  SIGNAL_HUP      129  Interrupted by HUP
  SIGNAL_INT      130  Interrupted by INT
  SIGNAL_TERM     143  Interrupted by TERM
```

Order by the workflow, not by number: success, then the outcomes a caller acts
on, then the error codes.

**In the consuming `SKILL.md`**, key the decision table on `RESULT` with the
code as a secondary column, so the agent matches on the string it just read:

```markdown
| RESULT         | Exit | Action                                            |
| -------------- | ---- | ------------------------------------------------- |
| `SUCCESS`      | `0`  | **Update mode.** Keep `PR_NUMBER`, `PR_BASE`, ... |
| `NO_PR_FOUND`  | `3`  | **Create mode.** Continue and create the PR ...   |
| `MULTIPLE_PRS` | `4`  | **STOP.** Show the candidates and ask which ...   |
```

State the reaction to `SCRIPT_FAILURE`, `PREFLIGHT_ERROR`, and the three signal
results too, even if it is just "STOP and report the blocker verbatim".

## Pin the Contract With a Test

The `RESULT=` value and its exit code are a contract a `SKILL.md` decision table
branches on, so a silent change to either breaks a caller that never runs the
script directly. Pin the outcomes an agent acts on with a test in the plugin's
`tests/` directory.

Resolve the script from the `plugin_root` fixture — `plugin_root / 'bin/...'` or
`plugin_root / 'skills/<name>/scripts/<script>.sh'` — never through a path that
climbs out of the plugin, which resolves nowhere once the plugin is installed
into a cache. Use `plugin_tmp_path` for scratch fixtures, and assert on the pair
that forms the contract:

```python
assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
    6,
    'RESULT=FETCH_FAILED',
)
```

Drive the script through a mock world rather than a live one: a throwaway `git`
repository built in the fixture directory, or stub `git`/`gh` executables placed
first on `PATH`. Existing plugin tests demonstrate mock repositories, stub tools,
and signal handling. These tests live with the plugin, not with any package that
happens to sit beside it in the developing repository.

## Definition of Done

- Every result an agent branches on is pinned by a test in the plugin's
  `tests/`, resolving the script through `plugin_root`.
- Every skill loads the sole result-code implementation from the plugin's
  shared `bin/result-codes.sh`; none copies or inlines its helpers.
- Every terminal path exits through `quit_by_code`; no bare `exit N` remains
  outside the shared result-code implementation.
- Exactly one declared, uppercase `RESULT=` value reaches stdout last.
- HUP, INT, and TERM emit exactly one matching `SIGNAL_*` result, re-raise the
  signal, and produce shell statuses `129`, `130`, and `143` respectively.
- Diagnostics and remediation advice are on stderr, not stdout.
- Metadata printed after streamed foreign stdout starts on its own line even
  when the foreign output is not newline-terminated.
- No workflow outcome exits `1`.
- Each code appears once in the script with one meaning.
- Every caller-supplied ref, range, path, or remote is resolved during
  preflight, so a bad argument becomes `PREFLIGHT_ERROR` rather than a `git`
  or `gh` crash surfacing as `UNKNOWN_CODE_128`.
- Every expected external-operation failure exits through a declared result
  while preserving useful diagnostics from the failed tool.
- Recurring situations use the same `RESULT` name as sibling skills.
- The `--help` table and the SKILL.md table list the same names and codes as
  the script.
- The script passes `shellcheck -x` and has been run for at least its success
  path and one branching failure path, with artifacts in `./.tmp/`.
