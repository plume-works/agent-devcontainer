---
name: python-format-lint
description: 'Format and lint Python in this repository with ruff — autofixes come from pre-commit and Super-Linter, verification from a fast non-mutating check. Use when formatting Python, fixing style/lint violations, organizing imports, or checking why a lint job fails in CI. Keywords: ruff, format, lint, isort, style, E501, I001, noqa, pre-commit, super-linter, python-lint-check.'
---

# Python Format & Lint (ruff)

This repository uses **ruff** for both formatting and linting, configured by
`.ruff.toml` at the repository root (line-length 99, single quotes, isort with
`force-sort-within-sections`).

There is exactly one ruff configuration and three places that run it:

| Runner                                   | What it does                                                      | When                    |
| ---------------------------------------- | ----------------------------------------------------------------- | ----------------------- |
| pre-commit (`ruff-format`, `ruff --fix`) | Formats and autofixes the staged files                            | Every local commit      |
| Super-Linter (`FIX_PYTHON_RUFF*`)        | Formats and autofixes in CI, then re-checks and commits the patch | `reformat.yml` in CI    |
| `python-lint-check.sh`                   | Non-mutating `ruff format --check` + `ruff check`                 | Manual, fast, no Docker |

**Import sorting needs no separate pass.** `I` is in `.ruff.toml`'s `select`
list, so a single `ruff check --fix` sorts imports too — that is why there is no
standalone isort step in pre-commit, in Super-Linter, or in any script.

Never judge compliance with stock `flake8` or `black` — their defaults (79-char
limit, double quotes, different isort grouping) produce false positives that do
not match this repo and do not fail CI.

## When to Use This Skill

- Formatting or cleaning up Python after editing source or tests
- A lint job fails in CI and you need to reproduce and fix it locally
- Organizing imports, fixing line length, or resolving import-group errors
- Deciding whether a `# noqa` is justified

## Workflow

1. **Check.** Start here — it is fast, needs no Docker, and tells you whether
   anything is wrong at all:

   ```bash
   python-lint-check.sh                        # everything
   python-lint-check.sh py_packages/validate_agent_files
   python-lint-check.sh path/to/file.py        # one file
   ```

2. **Apply autofixes.** Let pre-commit do it, so local and CI stay identical:

   ```bash
   pre-commit run ruff-format --files path/to/file.py
   pre-commit run ruff --files path/to/file.py
   ```

   Or invoke ruff directly for a tighter loop (config is picked up
   automatically):

   ```bash
   uv run ruff format path/to/file.py
   uv run ruff check --fix path/to/file.py
   ```

   To reproduce the full CI pass across every language, use the
   [local-reformat](../local-reformat/SKILL.md) skill.

3. **Fix remaining violations by hand.** Anything `ruff check --fix` cannot
   autofix must be fixed in the source. Use a targeted `# noqa: <rule>` **only**
   for a formatter-required incompatibility (e.g. `E203` on a slice); never
   disable a rule for a whole file or package. For import-group disagreements,
   adjust `lint.isort` in `.ruff.toml` rather than sprinkling `noqa`.

4. **Confirm clean.** Re-run step 1 until it exits zero with no output.

## Troubleshooting

| Symptom                                                   | Cause                                               | Fix                                                                                  |
| --------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `flake8` locally flags `E501` at 79 chars but CI is green | You ran stock `flake8`, not ruff                    | Use `python-lint-check.sh`; the repo limit is 99                                     |
| CI committed a formatting change you did not expect       | Super-Linter's autofix pass runs `ruff --fix`       | Run pre-commit locally before pushing so the fix lands in your commit                |
| Formatter keeps fighting your import order                | isort settings live in `.ruff.toml`                 | Adjust `lint.isort` there; do not add a separate isort pass                          |
| `ruff: command not found`                                 | The uv environment is not synced                    | Run `.devcontainer/scripts/uv-sync.sh` (or `uv sync`), then invoke ruff via `uv run` |
| Super-Linter reports ruff findings the local check misses | Version skew between the project ruff and the image | Run `scripts/validate-super-linter-tool-versions.sh`                                 |

## References

- Python coding conventions: the repository's root `AGENTS.md` (Python section)
- ruff configuration: `.ruff.toml` at the repository root
- Super-Linter flag generation: [super-linter-env.sh](../../bin/super-linter-env.sh)
