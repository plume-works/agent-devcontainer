---
type: task
description: Make an OpenCode e2e test whose seeded ChatGPT login is over its usage limit fail naming the usage limit, not "no assistant text".
stage: done
priority: low
created: 2026-10-20
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T00:15:10Z
sources:
- resource: scripts/e2e/iwe-workflows/harness_opencode.py
- resource: scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py
completed: 2026-10-20
---

# Name the usage limit when an OpenCode e2e run is refused

An OpenCode test in the IWE workflow e2e suite (`scripts/e2e/iwe-workflows/`)
whose seeded ChatGPT login is over its usage limit fails its run-completed
assertion with only "no assistant text". The transcript shows the provider
refusing every request with `subscription_sharing_usage_limit_exceeded`, but
`Transcript.auth_expired` in `harness_opencode.py` recognises only an expired
login (`{"type": "provider.auth"}`), so the failure reads like a suite fault.

The work: recognise the usage-limit refusal in the transcript and have the
run-completed assertion name it as the reason, the way it already names an
expired login. A reader of the test output then knows to wait for the limit to
reset instead of debugging the suite.

Verified anchor points (line numbers as of 2026-10-20):

- `scripts/e2e/iwe-workflows/harness_opencode.py:109` —
  `Transcript.usage_limited`
- `scripts/e2e/iwe-workflows/harness_opencode.py:113` —
  `Transcript.failure_reason`
- `scripts/e2e/iwe-workflows/test_iwe_workflows_opencode.py:27` — `run`, the
  run-completed assertion
