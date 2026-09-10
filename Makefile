.PHONY: help test smoke smoke-auto wake wake-memory wake-repeat test-harness validate check clean clean-claude

UV := $(shell command -v uv 2>/dev/null)

# Where the self-improve plugin lives in the catalog. Its live targets and its
# clean-up run from here, because `tests` is the plugin's own package name and
# resolves only from inside the plugin.
SELF_IMPROVE := .agents/plugins/self-improve

# Live tests skip at collection unless this is set, so no entry point — a path,
# a -m selection, a node id — can fire a paid session by accident. The targets
# below are the ones that mean to.
LIVE := SELF_IMPROVE_RUN_LIVE=1

# The model the *driving* sessions run on; the reviewer under test stays on
# SELF_IMPROVE_REVIEW_MODEL. `?=` leaves an exported shell value in charge, and
# `make wake SMOKE_MODEL=` restores the CLI's own default.
SMOKE_MODEL ?= sonnet
SMOKE_EFFORT ?= low
export SMOKE_MODEL SMOKE_EFFORT

# No default here: the suite's own is off, and duplicating it would give two
# places to change. This only forwards an override the caller supplied.
export SMOKE_AUTO_MEMORY

# An activated virtualenv in the developer's shell is not this project's
# environment; unset it so uv manages .venv without warning on every run.
unexport VIRTUAL_ENV

# Every live run gets its own test-runs/<label>_<nanosecond timestamp>/, so no
# two runs share a directory. Set per target below; a bare `pytest` run labels
# itself.
export TEST_RUN_LABEL

help:
	@echo "make test        run the offline suite (no model calls)"
	@echo "make smoke       run the packaged smoke test against a real Claude session"
	@echo "make smoke-auto  the same, skipping the one interactive check"
	@echo "make wake        verify the asynchronous wake automatically, on a pty"
	@echo "make wake-memory verify how the wake interacts with Claude's own auto memory"
	@echo "make wake-repeat run the wake check ten times to measure its stability"
	@echo ""
	@echo "make test-harness  self-check the pty harness against a fake terminal."
	@echo "                   Costs nothing and already runs inside 'make test';"
	@echo "                   this target reruns it alone, with the trace on."
	@echo ""
	@echo "What the smoke and wake driving sessions cost to run:"
	@echo "  SMOKE_MODEL=m  default sonnet; empty restores the CLI default"
	@echo "  SMOKE_EFFORT=l default low; empty restores the CLI default (high)"
	@echo "  SMOKE_AUTO_MEMORY=1 leave Claude's own auto memory on (default off:"
	@echo "                   it records the lesson first, so the reviewer defers)"
	@echo "  the reviewer under test has its own dials, unaffected by these:"
	@echo "  SELF_IMPROVE_REVIEW_MODEL (sonnet), SELF_IMPROVE_REVIEW_EFFORT (medium)"
	@echo ""
	@echo "Debugging the wake harness:"
	@echo "  WAKE_TRACE=0   silence the step-by-step trace (on by default)"
	@echo "  WAKE_BUDGET=n  override the per-check budget, in seconds"
	@echo "  the raw terminal stream of each run is left beside its workspace"
	@echo ""
	@echo "Where a live run leaves its output:"
	@echo "  test-runs/<target>_<timestamp>/<test>/  scratch repo, state, pty log"
	@echo "  test-runs/latest, test-runs/latest-<target>  symlinks to the newest"
	@echo "  every run keeps its own directory; nothing is overwritten"
	@echo ""
	@echo "make validate    validate the plugin and marketplace manifests with the Claude CLI"
	@echo "make check       test + validate"
	@echo "make clean       remove the plugin's caches and test-runs/, then clean-claude"
	@echo "make clean-claude  remove the ~/.claude/projects entries that test runs"
	@echo "                   leave behind, outside the repository where 'clean'"
	@echo "                   cannot reach them"
	@echo ""
	@echo "Formatting and linting are pre-commit's, not this Makefile's:"
	@echo "  pre-commit run --all-files"

ifeq ($(UV),)
test smoke smoke-auto wake wake-memory wake-repeat test-harness clean clean-claude:
	@echo "uv is required for development tooling."
	@echo "When the host lacks the toolchain, escalate rather than stopping"
	@echo "(AGENTS.md Best Practice 3): with a Docker daemon, run the command"
	@echo "through the devcontainer (/agentdev:microvm-sandbox); without one,"
	@echo "run it on a Codespace (/agentdev:remote-codespace-session)."
	@echo "The plugin itself needs no dependencies; this is only for tests."
	@exit 1
else
test:
	uv run --group dev pytest -q

# Spends real model usage, so it is never part of `make test` or `make check`.
# -rs matters: a check that could not reach the model observed nothing, and that
# must be readable rather than inferred. The scratch workspace is kept for triage.
smoke: TEST_RUN_LABEL := smoke
smoke:
	$(LIVE) uv run --group dev pytest $(SELF_IMPROVE)/tests -m smoke -s -v -rs

smoke-auto: TEST_RUN_LABEL := smoke-auto
smoke-auto:
	SMOKE_SKIP_INTERACTIVE=1 $(LIVE) \
	  uv run --group dev pytest $(SELF_IMPROVE)/tests -m smoke -s -v -rs

# Spec-0002. Drives a real interactive session on a pseudo-terminal. Opt-in on
# purpose: it spends model usage on two real reviews and is the most exposed to
# terminal-interface changes, so it never gates anything.
wake: TEST_RUN_LABEL := wake
wake:
	$(LIVE) uv run --group dev pytest $(SELF_IMPROVE)/tests \
	  -m "pty and not auto_memory" -s -v -rs

# The same exchange with auto memory left on. Auto memory records the lesson
# during the turn that teaches it, so the reviewer finds it already owned and
# declines — correct, but it would read as a broken wake.
wake-memory: TEST_RUN_LABEL := wake-memory
wake-memory:
	$(LIVE) uv run --group dev pytest $(SELF_IMPROVE)/tests \
	  -m "pty and auto_memory" -s -v -rs

# A self-check of the harness, not the plugin: it drives PtySession against a
# fake terminal, so if it passes, a stall belongs to the session under test. No
# model and no cost; this target only reruns them alone with the trace on.
test-harness:
	uv run --group dev pytest $(SELF_IMPROVE)/tests -m harness -s -v -rs

# Acceptance criterion 1: reliable across ten consecutive runs, stopping at the
# first failure. Numbering the label as well as stamping the time is what makes
# the ten sort in the order they ran.
wake-repeat:
	@for run in 1 2 3 4 5 6 7 8 9 10; do \
	  echo "=== wake run $$run/10 ==="; \
	  TEST_RUN_LABEL=wake-repeat-$$(printf '%02d' $$run) $(LIVE) \
	    uv run --group dev pytest $(SELF_IMPROVE)/tests \
	      -m "pty and not auto_memory" -q -rs || exit 1; \
	done
	@echo "=== ten consecutive wake runs, no failures ==="

clean:
	rm -rf $(SELF_IMPROVE)/.pytest_cache $(SELF_IMPROVE)/.ruff_cache test-runs
	find $(SELF_IMPROVE) -name __pycache__ -type d -prune -exec rm -rf {} +
	@$(MAKE) --no-print-directory clean-claude

# Live runs leave Claude project directories under ~/.claude, outside the
# repository, so `clean` cannot reach them; this prints each path before
# deleting it. Run from the plugin, where `tests` is unambiguous.
clean-claude:
	cd $(SELF_IMPROVE) && uv run python -m tests.smoke.workspaces
endif

# Validation needs a CLI new enough to know every hook event the plugin
# registers. An older one reports "Invalid key in record" for events it has
# never heard of, which is a toolchain gap rather than a manifest error.
validate:
	@command -v claude >/dev/null 2>&1 || { \
	  echo "claude CLI not found; skipping manifest validation"; exit 0; }
	@claude plugin validate ./$(SELF_IMPROVE) || { \
	  echo ""; \
	  echo "Installed Claude Code: $$(claude --version)"; \
	  echo "This plugin targets 2.1.196 or later. If the failure names a hook"; \
	  echo "event as an invalid key, the CLI predates that event."; \
	  echo "Upgrade with: npm install -g @anthropic-ai/claude-code"; \
	  exit 1; }
	@claude plugin validate .

check: test validate
