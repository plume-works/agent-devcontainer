---
name: iwe-plan
description: Create or revise implementation planning state — discovery in the real codebase first, then a coherent plan with verified code anchors, spec impact, and dependencies. Never edits implementation code.
disable-model-invocation: true
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Create or revise a plan

The Plan rulebook is the `iwe-planner` catalog agent. Run it here, in this
session, so you can ask the user about a material choice and wait for the
answer.

Read [the iwe-planner rulebook](../../agents/iwe-planner.agent.md) in full and
follow it in place for the topic or plan the user named, in its
**From `/agentdev:iwe-plan`** mode. Do not dispatch it as a subagent. Its
issue-closing step runs this skill's bundled `agent-code/close-issue.py`.
