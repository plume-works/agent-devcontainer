---
type: bug
description: In the devcontainer of a Claude Code cloud session, agentdev-runtime doctor fails its gh auth, git credential helper and github.com checks although gh and git authenticate through the session's agent proxy.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/doctor.py
- resource: .claude/startup.py
- resource: .devcontainer/docker-compose.yml
- resource: https://code.claude.com/docs/en/claude-code-on-the-web
stage: cancelled
severity: low
---

# Bug: doctor fails a healthy Claude Code cloud devcontainer

## Symptom

In a devcontainer that `.claude/startup.py` brought up in a Claude Code cloud
session, `agentdev-runtime doctor` ends `Overall: FAIL` with three GitHub
failures. Meanwhile `gh api user` returns the account, and `git ls-remote` and
`git push` to `origin` succeed:

- `gh auth` — `gh auth status` exits 1, and its output says "The token in
  GH_TOKEN is invalid";
- `git credential helper` — `not configured`;
- `github.com` — `curl -fsS https://github.com` exits 22 on HTTP 400.

## Reproduction

1. Start a Claude Code cloud session on this repository, so `.claude/startup.py`
   relays the agent proxy and writes `.devcontainer/cloud-session.env` (see
   [Cloud session host
   toolchain](../archive/3.0.0/architecture/cloud-session-host-toolchain.md)).
2. In the devcontainer, run `gh api user` and `git ls-remote origin`; both
   succeed.
3. Run `agentdev-runtime doctor`.

## Root cause

The three checks probe GitHub in ways the session's agent proxy does not serve,
although the access they stand for works:

- `gh auth status` validates the token with a GraphQL query, and the proxy
  answers `POST https://api.github.com/graphql` with 403. `gh` reports any
  failure of that query as an invalid token. REST calls with the same
  placeholder `GH_TOKEN` succeed, because the proxy replaces it with the real
  credential.
- No `credential.https://github.com.helper` exists because the proxy injects
  git's HTTP authentication, so git needs none. The check treats the absent
  helper as missing auth.
- The proxy answers the bare root `https://github.com/` with 400
  `"Request path could not be canonicalized."`, while it serves repository paths
  such as `https://github.com/plume-works/agent-devcontainer` with 200.

`doctor` has no notion of this environment: `main` distinguishes only the
`deploy` and `devcontainer` runtime modes, and nothing in the container says it
runs in a cloud session.

## Potential solution

Give `doctor` a Claude Code cloud environment. `.claude/startup.py` can mark it,
for example with a variable in `.devcontainer/cloud-session.env`. In that
environment, check `gh` with a REST call (`gh api user`), accept
`git ls-remote origin` authenticating in place of a configured credential
helper, and probe a repository path on `github.com` instead of the bare root.

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/doctor.py::auth` — `gh auth`
  through `gh auth status`
- `py_packages/agentdev_runtime/agentdev_runtime/doctor.py::auth` — the
  `credential.https://github.com.helper` lookup;
  `py_packages/agentdev_runtime/agentdev_runtime/doctor.py::auth` — its FAIL
- `py_packages/agentdev_runtime/agentdev_runtime/doctor.py::network` — the
  `https://github.com` probe
- `py_packages/agentdev_runtime/agentdev_runtime/doctor.py::runtime` — runtime
  mode checked against `PROFILES` (`deploy`, `devcontainer`)
