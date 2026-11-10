---
type: bug
stage: done
severity: medium
description: The AI task responder pushes with GITHUB_TOKEN, whose GitHub Actions app GitHub refuses as a ruleset bypass actor, so the iwe/** ruleset that blocks merges into dependent branches also rejects every responder push to an iwe/ branch.
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset
---

# Bug: the AI task responder cannot push to iwe/ branches under their ruleset

## Symptom

[Merges into dependent branches are
blocked](../../../../openspec/specs/stacked-prs/spec.md) by a ruleset on
`refs/heads/iwe/**` that requires the status check `base-is-main`, which no
workflow reports. A required status check applies to pushes as well as merges,
so every push to an `iwe/` branch is rejected (GH013) unless its pusher is a
bypass actor. The repository roles are; the AI task responder cannot be, so a
fix it is asked to push to an `iwe/` pull request branch is rejected.

## Reproduction

1. Create the ruleset with the GitHub Actions app as a bypass actor:
   `gh api -X POST repos/{owner}/{repo}/rulesets` with a `bypass_actors` entry
   `{"actor_id": 15368, "actor_type": "Integration", "bypass_mode": "always"}`
   and a `required_status_checks` rule for `base-is-main` on
   `refs/heads/iwe/**`.
2. GitHub answers HTTP 422: "Actor GitHub Actions integration must be part of
   the ruleset source or owner organization".
3. Without that entry, the ruleset is accepted, and a push made with a
   workflow's `GITHUB_TOKEN` to an `iwe/` branch is rejected.

## Root cause

The responder hands the workflow's `GITHUB_TOKEN` to the Claude action, so its
commits are pushed by the built-in GitHub Actions app (app id 15368). A ruleset
bypass list accepts only repository roles, teams, and GitHub Apps installed on
the repository's owner; the built-in app is none of these.

## Potential solution

Move every responder push onto the organization-owned `plume-works-quill` App,
then add that App to the `iwe/**` ruleset as a bypass actor in mode `always`.

## Fix

[Drop the free-form `@claude` task
responder](../plans/20261107-drop-claude-task-responder.md) removed the task
responder, the only responder job that pushed. No responder job holds
`contents: write` any more, so no responder push reaches an `iwe/` branch and
the ruleset needs no responder bypass actor.

## Key references

- `.github/workflows/ai-responder.yml#jobs.claude-task.container` —
  `claude-task`, the job holding `contents: write`
- `.github/workflows/ai-responder.yml#jobs` — `github_token` passed as
  `secrets.GITHUB_TOKEN`
- `.github/actions/run-claude-responder/action.yml#runs.steps.Claude Responder.with.github_token`
  — the token handed to `claude-code-action`
