## 1. Unblock the devcontainer change

- [x] 1.1 Change ruff resolution in `.agents/plugins/agentdev/bin/python-lint-check.sh` to try `uv run --no-sync` first, then an in-tree `.venv`, then `PATH`; keep the existing error message when all three miss
- [x] 1.2 Update the script's header comment, which currently explains the `.venv`-first preference
- [x] 1.3 Verify it passes in the devcontainer with no `.venv` present and reports the pinned ruff version
- [x] 1.4 Verify it still resolves a linter in a scratch project that has an in-tree `.venv` and no uv project

## 2. Devcontainer

- [x] 2.1 Set `UV_PROJECT_ENVIRONMENT` to `/uv/venvs/ws-project/` in `.devcontainer/devcontainer.json`
- [x] 2.2 Point `python.defaultInterpreterPath` and `ansible.python.interpreterPath` at `/uv/venvs/ws-project/bin/python3`
- [x] 2.3 Point `ansible.ansible.path` and `ansible.validation.lint.path` at `/uv/venvs/ws-project/bin/ansible` and `.../bin/ansible-lint`
- [x] 2.4 Remove the `ln -s` from `.devcontainer/scripts/uv-sync.sh` and narrow its removal to symlinks only, never a directory
- [x] 2.5 Rewrite the comment in `uv-sync.sh` that explains the symlink
- [x] 2.6 Leave `search.exclude`, `.gitignore`, `.dockerignore`, and the shellcheck/Super-Linter `.venv` exclusions in place

## 3. CI provisioning action

- [x] 3.1 In `.github/actions/setup-python-venv/action.yml`, drop the `python -m venv` step, the activate step, and the `VIRTUAL_ENV`/`GITHUB_PATH` exports
- [x] 3.2 Remove the now-unused `zizmor: ignore[github-env]` suppression that guarded the `GITHUB_ENV` write
- [x] 3.3 Add `UV_PYTHON_PREFERENCE: only-system` so uv binds to the interpreter `actions/setup-python` installed
- [x] 3.4 Replace the `actions/cache` step on `path: .venv` with `enable-cache` on `astral-sh/setup-uv`, and delete the `we just cache the venv-dir directly` comment
- [x] 3.5 Change the sync to `--locked --all-groups --all-extras`, dropping `--active` and replacing `--frozen`, which skips the lockfile currency check rather than enforcing it
- [x] 3.6 Update the action's `description` to state that it provisions but does not activate, and that callers must use `uv run`

## 4. CI callers

- [x] 4.1 Change the two `pytest` steps and the `validate_agent_files` step in `.github/workflows/validate-agent-files.yml` to `uv run`
- [x] 4.2 Align the sync flags at `.github/workflows/ci.yml:272` with the action's (`--locked --all-groups --all-extras`)
- [x] 4.3 Remove or rewrite the `ci.yml` comment about checking `validate_agent_files` before `uv sync` — with no activation anywhere, the project environment can no longer mask the image's copy

## 5. Shell helper

- [x] 5.1 Remove `venv_activate` from `ansible/roles/fish_setup/templates/dev.fish.j2`, keeping `find_up`
- [x] 5.2 Update `ansible/roles/fish_setup/README.md`, which lists the removed helper

## 6. Documentation

- [x] 6.1 Update the `setup-python-venv` row in `docs/knowledge/data/architecture/template-boundary.md` to describe the new contract, following `docs/knowledge/data/AGENTS.md`
- [x] 6.2 Fix `.agents/plugins/agentdev/skills/microvm-sandbox/SKILL.md`, which states that the sync script links `.venv`
- [x] 6.3 Fix `.agents/plugins/agentdev/skills/python-format-lint/SKILL.md`: the `.venv/bin/ruff` invocations and the two troubleshooting rows referencing `.venv`
- [x] 6.4 Record the breaking contract changes where contributors will see them — the action description, and the sync-script and fish-template comments

## 7. Verification

- [x] 7.1 Rebuild the devcontainer and confirm no `.venv` appears at the workspace root and `uv run python -V` reports 3.12 — verified by reproducing the new config in the running container (`uv run python -V` -> 3.12.3 at `/uv/venvs/ws-project/`, no workspace-root `.venv`); a true from-scratch rebuild is still pending, since rebuilding would terminate this session
- [x] 7.2 Confirm a terminal's `VIRTUAL_ENV` matches `UV_PROJECT_ENVIRONMENT` exactly and that `uv run` emits no mismatch warning — verified with both set to `/uv/venvs/ws-project/`; the warning seen in this pre-change session disappears
- [x] 7.3 Confirm the editor resolves the interpreter and both Ansible tool paths after the rebuild — all three configured paths (`python3`, `ansible`, `ansible-lint` under `/uv/venvs/ws-project/bin/`) exist and are executable
- [x] 7.4 Confirm a worktree that still holds the old `.venv` symlink has it cleared by one run of the sync script
- [x] 7.5 Run `uv run pytest py_packages .agents/plugins/agentdev/tests` and `python-lint-check.sh` in the rebuilt container — 136 passed, lint clean, run with no workspace `.venv` present
- [ ] 7.6 Confirm `validate-agent-files.yml` passes in CI, and that `pre-commit run --all-files` is unaffected — `pre-commit run --all-files` passes locally; the CI half needs a pushed branch
- [x] 7.7 Confirm lockfile drift fails at provisioning: with a dependency added to `pyproject.toml` and not locked, the sync step exits non-zero and no test step runs
