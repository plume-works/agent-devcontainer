---
name: skill-scripts
description: "Write and document a skill's bundled scripts so their outcome is readable by both a shell caller and an agent — a shared exit-code vocabulary, a RESULT= enum line on stdout, and the shared result_codes.py helpers. Use when adding or editing a Python script under a skill's agent-code/ directory, choosing or renumbering its exit codes, deciding what it prints, or wiring a SKILL.md step to branch on a script's outcome. Keywords: exit code, RESULT, result_codes.py, rc.run, Stop, script output contract."
---

# Skill Script Result Contract

A bundled script has two callers with different needs. A shell or test caller
branches on `$?` and needs numeric codes. An agent reads the tool result and
needs a self-describing outcome. Serve both: **keep the exit code, and name it
on stdout.**

Apply this to every script under a skill's `agent-code/` directory, the directory that
holds a skill's bundled code. Every such script is Python.

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

| Code  | Name              | Meaning                                                                                                                                                                                                                                                                                    |
| ----- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `0`   | `SUCCESS`         | The script did what it was asked.                                                                                                                                                                                                                                                          |
| `1`   | `SCRIPT_FAILURE`  | The script broke. **Never give `1` a workflow meaning** — an uncaught exception produces it, so a deliberate `1` is indistinguishable from a crash. Deliberately reporting a breakage _as_ a breakage (returning `1` when a delegate returns something impossible) is the one correct use. |
| `2`   | `PREFLIGHT_ERROR` | Bad usage, or the environment cannot support the operation at all: not a repo, detached HEAD, missing required argument.                                                                                                                                                                   |
| `3`+  | script-specific   | Outcomes the caller must branch on. Number them in the order the workflow meets them and stay at or below `125`.                                                                                                                                                                           |
| `129` | `SIGNAL_HUP`      | The process received HUP (`128 + 1`). The result is emitted before the signal is re-raised.                                                                                                                                                                                                |
| `130` | `SIGNAL_INT`      | The process received INT (`128 + 2`). The result is emitted before the signal is re-raised.                                                                                                                                                                                                |
| `143` | `SIGNAL_TERM`     | The process received TERM (`128 + 15`). The result is emitted before the signal is re-raised.                                                                                                                                                                                              |

Codes `126`, `127`, and `128+N` are shell-reserved, since a shell caller reads
the status. The shared implementation uses the conventional `129`, `130`, and
`143` statuses only for HUP, INT, and TERM; never override them with workflow
meanings.

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

A script is Python on `#!/usr/bin/env python3` and imports nothing beyond the
standard library: it ships in the plugin cache of any consuming repository and
runs on whatever host runs the agent, where nothing is installed for it. It
reaches the plugin's shared `bin/` modules through `sys.path`, resolved from the
script's own location, so it works from a repository checkout and from an
installed plugin cache alike. Never copy or inline the shared helpers into a
skill.

```python
#!/usr/bin/env python3

"""Find the pull request whose head is the current branch."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import print_error, require_git_repo, Stop  # noqa: E402

NO_PR_FOUND = 3
MULTIPLE_PRS = 4


def run(arguments: list[str]) -> int:
    """Look up the branch's pull request and report it."""
    ...
    print('PR_FOUND=false')
    return NO_PR_FOUND


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update({NO_PR_FOUND: 'NO_PR_FOUND', MULTIPLE_PRS: 'MULTIPLE_PRS'})
    rc.install()
    rc.run(main)
```

`bin/result_codes.py` owns the contract. `rc.install()` installs the exit hook,
the exception hook, and the HUP, INT, and TERM handlers; `rc.run(main)` exits
with the code `main` returns after printing its `RESULT` line. **Never print
`RESULT=` yourself.** An uncaught exception still ends as
`RESULT=SCRIPT_FAILURE` with status `1`, and a terminating signal prints its
`SIGNAL_*` result, restores the default action, and re-raises the signal, so a
shell caller observes `129`, `130`, or `143` and the operating system records a
genuine signal death.

`bin/skill_common.py` holds what every script needs: `print_error` (the
`ERROR: ` line on stderr), `Stop` (raised by a helper to end the run with a
declared code, caught once in `main`), `require_git_repo`, `current_branch`,
`help_header`, `bash_quote` (bash's `printf %q`, for a command line a shell will
re-read), and the subprocess runners below. Shared code that only one skill's
scripts use lives beside them as `agent-code/<name>_common.py`, imported by
name, since the script's own directory is on `sys.path`. Code two skills share
moves to `bin/`; a skill never imports a sibling skill's code.

Declare the script's codes as module constants and register their names in the
`__main__` block, before `rc.install()`. A helper deep in the call stack ends
the run with `raise Stop(CODE)` after printing its diagnostic, so every
terminal path still reaches `rc.run`.

## Guard External Commands and Validate Their Products

Run tools through the `skill_common` runners, which never raise on a non-zero
status and keep stdout for the script's product:

- `run_tool(...)` captures stdout and stderr, for a value the script reads.
- `run_to_stderr(...)` sends the tool's stdout to stderr, for chatter that
  narrates rather than reports (`git push`, `git stash pop`).
- `run_inherited(...)` passes the tool's output straight through, for output
  that _is_ the product (`git log`, a `git diff` section).

The last two flush the script's own stdout first, so lines stay in order.
**Check every status whose meaning could be mistaken for yours**, decide what it
means, and return a code you declared. Keep the tool's stderr visible when it
explains the failure:

```python
if run_inherited('git', 'fetch', remote):
    print_error(f"Failed to fetch remote '{remote}'.")
    return FETCH_FAILED
```

A successful external call validates only what it actually did. Fetching a
reachable remote does not prove a caller-supplied branch exists. Resolve refs,
ranges, paths, IDs, and similar inputs explicitly before passing them to a
later command:

```python
base_ref = f'{remote}/{base}'
if run_tool('git', 'rev-parse', '--verify', '--quiet', f'{base_ref}^{{commit}}').returncode:
    print_error(f"Base branch '{base_ref}' does not exist.")
    return PREFLIGHT_ERROR
```

Classify the two failures separately: an invalid caller-supplied identifier is
a preflight error, while an attempted routine operation that the caller may
handle differently gets its own declared result such as `FETCH_FAILED`.
`UNKNOWN_CODE_<n>` in a real run is a bug report against the script, not a
reason to widen the table. Parse JSON with the `json` module rather than
calling `jq`, which a consuming host may lack.

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

```python
status = run_inherited('gh', 'codespace', 'ssh', '-c', name, '--', remote_command)
print(f'\nREMOTE_EXIT_CODE={status}')
if status:
    return REMOTE_COMMAND_FAILED
return 0
```

The unconditional separator may produce a blank line when the foreign output
was already newline-terminated; preserving a parseable contract is more
important than suppressing that harmless whitespace.

Nothing is lost — the exact status is still there for a caller that needs it
(`pytest` 1 vs 5), and `&&` chaining still short-circuits. Say so in `--help`,
since it changes the script's shell-level contract.

## Delegating to Another Script

When a script hands part of its work to a sibling script, **align the two code
tables** so a shared situation carries the same number _and_ the same name in
both — the natural outcome of the naming rule above. Run the delegate with its
stdout captured, forward every line but its `RESULT` line, and translate its
status: two `RESULT=` lines are worse than none, since a reader takes the last
one. Send an unrecognized delegate status to `1`:

```python
helper = subprocess.run(
    [str(MERGE_SCRIPT), source], check=False, stdout=subprocess.PIPE, text=True
)
for line in helper.stdout.rstrip('\n').split('\n'):
    if not line.startswith('RESULT='):
        print(line)
if helper.returncode not in (0, MERGE_CONFLICTS, PREFLIGHT_ERROR):
    raise Stop(1)
```

Guard the handoff first: check that the delegate exists and is executable, and
report a missing one as `1`.

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
`plugin_root / 'skills/<name>/agent-code/<script>.py'` — never through a path that
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
- The script imports only the standard library and the plugin's `bin/`
  modules, and `python3 -S agent-code/<script>.py --help` runs, proving it needs
  nothing installed.
- Every skill loads the sole result-code implementation from the plugin's
  shared `bin/result_codes.py` through `rc.install()` and `rc.run(main)`; none
  copies or inlines its helpers, and none prints `RESULT=` itself.
- Every terminal path returns a declared code from `main` or raises `Stop`; no
  `sys.exit(N)` with a workflow meaning remains outside `main`.
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
  or `gh` failure surfacing as `UNKNOWN_CODE_128`.
- Every expected external-operation failure exits through a declared result
  while preserving useful diagnostics from the failed tool.
- Recurring situations use the same `RESULT` name as sibling skills.
- The `--help` table and the SKILL.md table list the same names and codes as
  the script.
- The script passes `ruff` and has been run for at least its success path and
  one branching failure path, with artifacts in `./.tmp/`.
