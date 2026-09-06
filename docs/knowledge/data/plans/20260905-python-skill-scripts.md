---
type: plan
description: Port stale-map-docs.sh to Python behind an unchanged RESULT= contract, on a shared result_codes.py helper.
created: 2026-09-05
generated:
  by: claude-code/opus-5
  at: 2026-09-05T00:00:00Z
---

# Python skill scripts

## Context

[Pin bumps invalidate map docs](../bugs/pin-bumps-invalidate-map-docs.md) is
fixed by masking machine-managed content out of `source_digest` before hashing.
That fix needs glob matching, JSON parsing, and per-file regex substitution —
work that bash does badly and that `stale-map-docs.sh` would have to grow
subprocess-per-file to reach.

Porting first, on its own, keeps the two changes separable. A port that computes
byte-identical digests and emits identical `RESULT=` lines is provable against
the suite that already exists; once it is in, any digest mismatch in the masking
work is unambiguously a masking defect.

The port also removes a duplicate. `test_stale_map_docs.py:38-61` reimplements
the digest algorithm in Python so it can assert against the bash original — a
second copy that masking would have to grow too. A Python script lets the test
import the function instead.

`stale-map-docs.sh` is the first script in the catalog that wants Python; every
other script under `skills/*/scripts/` is bash, and the ones that report a
`RESULT=` line source `bin/result-codes.sh`. So the `RESULT=` contract needs a
Python implementation, and it belongs beside the bash one rather than inside the
first script that needs it.

## Approach

Replace `stale-map-docs.sh` with `stale-map-docs.py` outright, rather than
keeping a bash shell that calls a Python helper. A hybrid splits the digest
algorithm across two languages and marshals arguments between them for no gain.

Add `bin/result_codes.py` implementing the same contract as
`bin/result-codes.sh`: a code-to-name table, `RESULT=<NAME>` as the last line of
stdout on every exit path, and terminating signals named and then **re-raised**
so a shell caller still observes signal death. `test_result_codes.py` asserts a
negative `returncode` for each signal, so `sys.exit(128 + signum)` is not
equivalent — the Python helper restores the default handler and re-signals
itself.

Frontmatter parsing moves from hand-rolled awk to a parser that handles the YAML
subset the schemas permit. The awk in `scalar_field` and `source_paths`
mis-reads quoted values containing colons and multi-line scalars; the port is a
chance to stop carrying that, and the schemas bound in `.iwe/config.toml`
constrain what shapes must be read.

Stdlib only. The script is a template artifact that consuming repositories
receive through `template-consume`, where this repository's `uv` environment
does not exist, so it runs under `#!/usr/bin/env python3` with no third-party
imports.

Rejected: keeping bash and shelling out to `yq` or `python3 -c` for the hard
parts. The script must run on a stock image with no dependency beyond `python3`,
and inline Python inside bash is neither testable nor lintable.

## Implementation Steps

### Task 1: Add the shared Python result-code helper

**Files:** Create: `.agents/plugins/agentdev/bin/result_codes.py`

- [x] Implement the contract from `bin/result-codes.sh`: a mutable code-to-name
  mapping seeded with `0=SUCCESS`, `1=SCRIPT_FAILURE`, `2=PREFLIGHT_ERROR`,
  `129=SIGNAL_HUP`, `130=SIGNAL_INT`, `143=SIGNAL_TERM`; a `quit_by_code`
  equivalent that prints `RESULT=<NAME>` to stdout and exits with the code; an
  unknown code rendering as `UNKNOWN_CODE_<n>` as `emit_result` does.
  - **Evidence:** `RESULT_CODES` and `quit_by_code` in `bin/result_codes.py`;
    `test_python_unknown_code_renders_as_unknown` covers the `UNKNOWN_CODE_<n>`
    rendering.
- [x] Guarantee `RESULT=` is emitted exactly once and last on every path,
  including an uncaught exception, via an `atexit` hook mirroring
  `report_unhandled_exit`. An uncaught exception exits `1` with its traceback on
  stderr.
  - **Evidence:** `test_python_result_line_is_last_on_a_normal_exit` and
    `test_python_result_line_is_last_on_an_uncaught_exception` pass; the `run`
    entry point also names a bare `sys.exit`, covered by
    `test_python_bare_exit_is_named_like_the_shell_helper`.
- [x] Install HUP/INT/TERM handlers that emit the result, restore
  `signal.SIG_DFL`, and re-raise with `os.kill`, so the caller sees `-SIGINT`
  rather than a normal exit of 130 — matching `report_signal` at
  `bin/result-codes.sh:62-72`.
  - **Evidence:** `test_python_result_codes_preserve_terminating_signals`
    asserts the same `(-signal, 129/130/143, RESULT=SIGNAL_*)` triples as the
    bash case.

### Task 2: Cover the Python helper in the result-codes test

**Files:** Modify: `.agents/plugins/agentdev/tests/test_result_codes.py`

- [x] Add a case asserting the Python helper produces the same
  `(returncode, shell_status, stdout)` triples the existing bash case asserts at
  `test_result_codes.py:42-46`: negative return codes for HUP/INT/TERM, statuses
  129/130/143, and the matching `RESULT=SIGNAL_*` line.
  - **Evidence:** `test_python_result_codes_preserve_terminating_signals` in
    `tests/test_result_codes.py`, asserting the identical triple dict.
- [x] Assert `RESULT=` is last on a normal-exit path and on an uncaught
  exception, which the bash case does not cover for either implementation.
  - **Evidence:** `test_python_result_line_is_last_on_a_normal_exit` and
    `test_python_result_line_is_last_on_an_uncaught_exception` assert the exact
    stdout line sequence.

### Task 3: Port the script, preserving digests and output byte-for-byte

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py`; Delete:
`.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh`

- [x] Reproduce every stdout line and count key from `usage()` at
  `stale-map-docs.sh:16-46`: `MAP_DIR`, the per-doc `FRESH`/`STALE`/
  `GONE`/`UNKNOWN_COMMIT`/`EXPIRED`/`NO_COMMIT` lines with their exact field
  order, then `DOC_COUNT`, `FRESH_COUNT`, `STALE_COUNT`, `GONE_COUNT`,
  `EXPIRED_COUNT`, then `RESULT=`. Register `3=STALE_FOUND` and `4=NO_MAP_DOCS`
  as `stale-map-docs.sh:14` does.
  - **Evidence:** Both scripts run on this checkout produce byte-identical
    stdout over 26 docs (15 fresh, 11 stale) and the same exit 3, in the commit
    that ports the script.
- [x] Reproduce `source_digest_for_paths` exactly (`stale-map-docs.sh:141-162`):
  `git ls-files -z` over the source paths, deduplicated and sorted bytewise,
  each entry contributing `<path>\0<git hash-object output>\0` — or `MISSING`
  for a listed path absent from the worktree — hashed with sha256 and prefixed
  `sha256:`. An empty path list hashes the empty string.
  - **Evidence:** Every `source_digest` recorded in `data/codebase/**/*.md` is
    unchanged, and the 11 STALE digest values match the shell original's
    byte-for-byte in the same comparison run.
- [x] Preserve `--library` and `-h/--help`, help text on stdout exiting
  `SUCCESS`, and unknown arguments to stderr exiting `PREFLIGHT_ERROR`. Preserve
  the `.iwe/config.toml` `[library].path` lookup and the not-a-repo and
  missing-config preflight errors (`stale-map-docs.sh:70-95`).
  - **Evidence:** `--help`, `--bogus`, a valueless `--library`, an explicit
    `--library docs/knowledge`, and a run outside any repository each match the
    shell original's exit code, stdout, and stderr; the only difference is the
    script's own filename in its usage line. Covered by `test_help_is_a_success`
    and `test_missing_iwe_config_is_a_preflight_error`.
- [x] Preserve the legacy `commit` fallback for docs without `source_digest`,
  including `UNKNOWN_COMMIT` via `git cat-file -e` and the
  `git log --oneline <commit>..HEAD` touch count (`stale-map-docs.sh:210-232`).
  - **Evidence:** `test_commit_touching_a_source_marks_the_doc_stale` and
    `test_unknown_commit_and_past_stale_after_are_flagged` pass unchanged.
- [x] Parse frontmatter with a reader that handles quoted scalars containing
  colons and the three `source` shapes (scalar, flow list, block list) that
  `source_paths` handles at `stale-map-docs.sh:123-139`.
  - **Evidence:** `source_paths` covers all three shapes; the suite exercises
    scalar, flow-list, and block-list `source` values and passes unchanged.

### Task 4: Point the existing suite at the ported script

**Files:** Modify: `.agents/plugins/agentdev/tests/test_stale_map_docs.py`

- [x] Change `SCRIPT_PATH` at `test_stale_map_docs.py:11` to the `.py` file.
  Every existing behavior test passes unchanged — that is the port's acceptance
  criterion, so do not adjust assertions to fit the port.
  - **Evidence:** `uv run pytest .agents/plugins/agentdev/tests` — 48 passed;
    `git diff HEAD` over the test file shows no changed assertion lines.
- [x] Replace the reimplemented `source_digest` helper at
  `test_stale_map_docs.py:38-61` with an import of the ported function, so the
  algorithm has one definition.
  - **Evidence:** the test's `source_digest` now delegates to
    `stale_map_docs.source_digest_for_paths`, loaded by `_load_script_module`.

### Task 5: Update the references to the script's filename

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-map/SKILL.md`;
`.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`;
`docs/knowledge/data/spec/iwe-workflow-skills.md`; `docs/knowledge/AGENTS.md`

- [x] Rename the script in `iwe-map/SKILL.md` at lines 115, 123, 149, 193, and
  229, in `iwe-verify/SKILL.md:85`, in `AGENTS.md:60`, and in the `sources:`
  entry of `data/spec/iwe-workflow-skills.md:13`.
  `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)` at `iwe-map/SKILL.md:5`
  already admits a `.py` file and needs no change.
  - **Evidence:** all eight references renamed (five in `iwe-map/SKILL.md`, one
    each in the other three files); `grep stale-map-docs\.sh` over those four
    files returns nothing, and
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 47/47 skills valid with 0 errors.
- [x] Leave the historical references in `data/plans/20260903-iwe-map-skill.md`
  and `data/bugs/missing-map-skill.md` alone: they record what shipped then.
  - **Evidence:** `git diff --name-only` over both files is empty; they still
    name the `.sh`.

### Task 6: Re-anchor the documents citing the deleted script

**Files:** Modify: `docs/knowledge/data/bugs/pin-bumps-invalidate-map-docs.md`;
`docs/knowledge/data/plans/20260905-digest-masks.md`;
`docs/knowledge/data/architecture/agent-metadata-files.md`

- [ ] Re-locate every `## Key references` anchor in those three files that cites
  a `stale-map-docs.sh` line number against `stale-map-docs.py`, and restamp
  each file's `Verified anchor points (line numbers as of ...)` line. Deleting
  the `.sh` breaks all of them; they are pointers meant to resolve, not history.
  `grep -n 'stale-map-docs\.sh:' docs/knowledge/` enumerates the live set, which
  changes as those plans are revised.
- [ ] Update the bug's `sources:` entry naming the `.sh` file. Leave its Symptom
  and Reproduction prose alone — those record an observation made against the
  script as it then was.

## Spec changes

None — no behavioral change. `data/spec/iwe-workflow-skills.md` names the script
under `sources:` and gets a filename correction in Task 5, not a requirement
change: every result code, output line, and digest value is unchanged by this
plan, which is what makes the port provable.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_stale_map_docs.py` passes
  with assertions unchanged from before the port.
- `uv run pytest .agents/plugins/agentdev/tests/test_result_codes.py` passes,
  covering both helper implementations.
- Digest equivalence on the real library: the digest recorded in every
  `data/codebase/**/*.md` frontmatter is unchanged, and `stale-map-docs.py`
  reports the same per-doc verdicts as the bash script did on the same commit.
  No `source_digest` value in the repository is edited by this plan.
- The pre-commit ruff hook accepts the new Python: `uv run ruff check` and
  `uv run ruff format --check` on both new files.
- `${CLAUDE_SKILL_DIR}/scripts/stale-map-docs.py` ends `RESULT=SUCCESS` on the
  current checkout, as `iwe-map/SKILL.md:229` requires before a map commit.
- No forward-looking document anchors the deleted script. Grepping
  `stale-map-docs\.sh:` across the bug, the digest-masks plan, and
  `data/architecture/agent-metadata-files.md` returns nothing once Task 6 lands.
  This plan's own anchors and `data/plans/20260903-iwe-map-skill.md` keep citing
  the `.sh` deliberately: they record the script this port consumed and the work
  that built it, not pointers a future session should follow.

## Out of scope

- Digest masking, `.agent.metadata.json`, and any change to what content the
  digest covers — that is the plan this one unblocks.
- Porting the remaining bash scripts under `skills/*/scripts/`.
  `bin/result-codes.sh` stays, and stays the implementation they source.
- Changing the `RESULT=` vocabulary, exit codes, or output keys.

## Key references

Verified anchor points (line numbers as of 2026-09-05):

- `.agents/plugins/agentdev/bin/result-codes.sh:15-23` — `RESULT_CODES`, the
  canonical code-to-name table
- `.agents/plugins/agentdev/bin/result-codes.sh:26-49` — `emit_result` and
  `quit_by_code`
- `.agents/plugins/agentdev/bin/result-codes.sh:62-72` — `report_signal`, which
  restores the default handler and re-raises
- `.agents/plugins/agentdev/bin/result-codes.sh:74-77` — the EXIT and signal
  trap installation
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:14` — the
  script's own `STALE_FOUND` and `NO_MAP_DOCS` registrations
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:16-46` —
  `usage`, which documents every output line the port must reproduce
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:109-139` —
  `frontmatter_of`, `scalar_field`, and `source_paths`, the awk parsers
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:141-162` —
  `source_digest_for_paths`, the algorithm the port must preserve exactly
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:215-232` —
  the legacy `commit` fallback
- `.agents/plugins/agentdev/tests/test_stale_map_docs.py:11` — `SCRIPT_PATH`
- `.agents/plugins/agentdev/tests/test_stale_map_docs.py:38-61` — the
  reimplemented digest the port replaces with an import
- `.agents/plugins/agentdev/tests/test_result_codes.py:42-46` — the signal
  triples the Python helper must match
- `.agents/plugins/agentdev/tests/conftest.py:21-24` — the `plugin_root`
  fixture, which resolves from the plugin tree rather than this repository
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:5` — `allowed-tools`, whose
  glob already admits a `.py` script
