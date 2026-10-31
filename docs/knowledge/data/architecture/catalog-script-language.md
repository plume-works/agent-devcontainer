---
type: architecture
description: Every script the agentdev catalog ships under bin/ and skills/*/agent-code/ is standard-library-only Python that reaches the shared bin/ modules through sys.path, because the catalog runs from any consuming repository's plugin cache on a host that installs nothing for it.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T00:02:25Z
sources:
- resource: .agents/plugins/agentdev/bin/result_codes.py
- resource: .agents/plugins/agentdev/bin/skill_common.py
- resource: .agents/plugins/agentdev/skills/skill-scripts/SKILL.md
- resource: .agents/AGENTS.md
---

# Catalog script language

## Decision

Every script under the agentdev plugin's `bin/` and `skills/*/agent-code/` is
Python on `#!/usr/bin/env python3` that imports only the standard library. A
script reaches the shared modules in `bin/` by inserting that directory into
`sys.path`, resolved from its own file location:

``` python
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))
```

The shared modules are `result_codes` (the `RESULT=` contract, its exit and
signal hooks), `skill_common` (diagnostics, the declared-stop exception, the
subprocess runners, `bash_quote`), and the topic modules `git_default_branch`,
`github_issue`, and `super_linter`. Code that only one skill's scripts share
lives beside them as `agent-code/<name>_common.py`. The output contract itself
is the `skill-scripts` skill's.

## Constraints

- **The plugin cache has no install step.** The catalog ships in the plugin
  cache of whatever repository enables it and runs on whatever host runs the
  agent, where this repository's `uv` environment does not exist. A script may
  therefore depend on `python3` and the tools it drives (`git`, `gh`), and on
  nothing installed for it. `python3 -S <script> --help` running proves the
  standard-library rule for a script whose `--help` is its own.
- **Paths resolve from the script, never from the repository.** A path written
  relative to this repository resolves nowhere once the plugin is installed;
  `Path(__file__)` resolves the same in a checkout and in a cache.
- **A skill never imports a sibling skill's code.** Code two skills share moves
  to `bin/`.
- **External tool contracts carry over unchanged.** Where a command line is
  handed to a shell, as an SSH remote command or a printed `gh` invocation, it
  is quoted by `bash_quote`, which reproduces bash's `printf %q`, so the shell
  that re-reads it sees the words the script meant.

## Rejected alternatives

- **A Python package installed into the plugin.** A plugin cache has no install
  step, so the package would be absent exactly where the scripts run. `sys.path`
  to `bin/` needs nothing installed.
- **Bash wrappers around Python helpers.** One algorithm split across two
  languages is tested and linted as neither.
- **Shell scripts with `jq`, `awk`, and `sed` for the hard parts.** Each tool is
  a host dependency the consuming repository may lack, and the logic between
  them is untestable short of running the whole script.

## Related

- [Python skill scripts](../plans/20260905-python-skill-scripts.md) — the first
  catalog script ported, and the origin of `bin/result_codes.py`.
- [Port the catalog's bundled shell scripts to
  Python](../plans/20261029-catalog-scripts-python.md) — the port of the rest.
