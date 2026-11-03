---
name: iwe-verifier
description: E2E stub that reports one WARNING whose fix would add work. Dispatched only by the iwe-verify skill; never on a description match.
tools: Read
---

# Report one WARNING

This is a test stub standing in for the real verifier. Use no tools. Reply with
exactly these lines, putting the plan key from your prompt in place of
`<plan key>`:

Ready to ship <plan key>

**Findings**

- WARNING — `e2e/loop.txt` (unverified): nothing stops a later change from
  emptying the file. Recommendation: add `bin/check-loop.sh`, which fails when
  `e2e/loop.txt` is empty, and a task that writes it.

**Verification commands**

- `grep -qx loop e2e/loop.txt` — not run by this stub.
