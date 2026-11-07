---
name: tdd
description: Run the Red, Green, Refactor cycle in this session — one failing test, the minimal code to pass it, then cleanup with tests green. Use only when TDD or Red-Green-Refactor is asked for by name, or when the Principal Engineer agent directs it. Never test text files, only real executable code logic.
---

# Test-Driven Development

Run one Red → Green → Refactor cycle per behavior, in this session. Verify each
phase before starting the next: the test fails for the right reason, then
passes, then still passes.

## When TDD applies

**Never test text files — only real executable code logic.**

Use the cycle only for features, bug fixes, or critical logic in runtime
executable code whose behavior an automated unit or integration test can
exercise.

Never use it for documentation, Markdown, configuration, manifests, CI
workflows, lockfiles, templates, prompts, agent definitions, skill instructions,
or other declarative artifacts. Modify those directly and run their existing
formatter, linter, parser, schema, syntax, or catalog validation. Never create a
test that only duplicates an artifact's contents to manufacture a Red phase.

For mixed work, run the cycle only for the runtime executable behavior and
handle the other artifacts directly. Updating an existing test, fixture, or
snapshot without changing production behavior needs no new cycle.

## Running tests

- **Python** — always `pytest`, never `unittest`: `uv run pytest <path>::<test_name>`
  for one test, `uv run pytest <path>` for its file. Run `uv sync` first if a
  dependency was added.
- **JavaScript / TypeScript** — `bun test <path>`, with colocated `*.test.ts` files.
- Scope to the narrowest target while iterating; run the full suite only when asked.

## Red — write one failing test

Take the requirements from the request: a spec file path or an issue number
(`gh issue view <n>`). If they are too ambiguous to write a failing test, ask
the user; dispatched, stop and report the open questions.

- **Test before code** — write no production code without a failing test.
- **One test at a time** — one behavior per cycle, structured Arrange / Act / Assert.
- **Be specific** — the test expresses exactly one expected behavior. Prefer
  several small, focused test files over one monolith.
- **Fail for the right reason** — run it and confirm it fails because the
  implementation is missing, not from a syntax or import error.

## Green — make it pass

1. **Run the failing test** to confirm exactly what must be implemented.
2. **Write just enough code** to pass it. Start with a hard-coded return and
   generalize as more tests force it; when the solution is obvious, write it
   directly. Do not anticipate requirements beyond the current test.
3. **Run the surrounding tests** so existing behavior stays unbroken.
4. **Leave the test unchanged** from the Red phase.

Duplication and design smells wait for Refactor.

## Refactor — improve quality

Start only from green tests, and keep observable behavior unchanged. Make one
small improvement at a time, running the tests after each.

- **Remove duplication** and **simplify complexity** — extract shared code, break
  down large functions, reduce branching.
- **Improve readability** — intention-revealing names, single-responsibility
  functions, SOLID applied where it helps.
- **Follow language conventions** — Python per PEP 8 and the repository's
  type-hint, docstring, and exception-handling rules in `AGENTS.md`. JavaScript
  and TypeScript prefer immutable data, narrow types, and explicit error handling
  over silent fallbacks.
- **Harden lightly** — validate external inputs at boundaries, and never hard-code
  credentials or tokens.

Finish with the gates CI enforces: `python_lint_check.py` for Python, with
autofixes from `pre-commit run --files <paths>`, then the tests.

## Report

State what each phase did and list technical-debt follow-ups as suggested issue
text. Do not comment on or close GitHub issues.
