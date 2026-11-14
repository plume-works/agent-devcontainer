---
type: bug
description: CI builds the ubuntu-ansible image without a revision label. Thus the promote guard that keeps a tag on the newest commit cannot read the label, and it always moves the tags of that image.
stage: pending
severity: medium
sources:
- resource: .github/workflows/ci.yml
- resource: .github/actions/docker/build-push-action/select-labels.sh
- resource: .github/actions/docker/promote/action.yml
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the promote step can move the `ubuntu-ansible` tags to an older image

## Symptom

A published tag must name only a tested image, and a re-run of an older CI run
must not move a tag back. For `ubuntu-ansible`, the promote step does not stop a
tag from moving back. When an older run promotes after a newer run, the moving
tags of `ubuntu-ansible` name the older image.

## Reproduction

1. Let CI promote the images for commit B, a descendant of commit A.
2. Re-run the CI run for commit A, so that it promotes again.
3. The promote step skips the tags of the other images with "Skipping ...: it
   names B". It moves the `ubuntu-ansible` tags to the image of commit A.

## Root cause

`.github/workflows/ci.yml#jobs.build-dev-image` builds `ubuntu-ansible` with
`stable-labels: 'true'`. With it,
`.github/actions/docker/build-push-action/select-labels.sh` removes
`org.opencontainers.image.revision`. The guard in
`.github/actions/docker/promote/action.yml` reads that label. When the label is
empty, the guard does not skip the tag.
