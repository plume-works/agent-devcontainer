---
type: task
stage: pending
priority: low
created: 2026-11-24
description: Keep scripts/check-anchors.py from reading a back-ticked name@ref span, such as a GitHub Action ref or a plugin id, as a code anchor.
sources:
- resource: scripts/check-anchors.py
- resource: https://github.com/plume-works/agent-devcontainer/pull/991
---

# Skip name@ref spans that are not anchors in the anchor checker

A code anchor separates the file from the symbol with `@`
(`schema/code-anchors.md`). `scripts/check-anchors.py@ANCHOR` therefore matches
any back-ticked span of the form name@ref — a GitHub Action ref like
actions/checkout@v4, a plugin id like expo@claude-plugins-official, a package
pin like pkg@1.2.3, an e-mail address. `scripts/check-anchors.py@anchors` skips
only all-digit fragments, so in a live document (a guide, an open bug or task,
an active plan's `## Key references`) such a span is reported as an unresolved
anchor and the `check-anchors` pre-commit hook blocks the commit. The examples
here are not back-ticked for that reason. No live document holds one yet; the
first guide or bug that names an action, plugin, or package version will.

The fix: count a span as an anchor only when its path part has a file extension
or names a Makefile, Dockerfile, or Containerfile, so an anchor to a missing
file is still reported. A test pins that actions/checkout@v4 and
name@marketplace are not checked.
