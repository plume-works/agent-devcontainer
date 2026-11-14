---
type: hub
description: Bug reports, investigations, and repro notes.
stage: living
---

# 🐛 Bugs

*One document per open bug in `bugs/<slug>.md`, listed here; a done or cancelled
bug moves to `archive/` and leaves this list. Its title, body sections, and
stages are defined under Bugs in `SCHEMA.md` and enforced by
`.iwe/schemas/bug.yaml`.*

[Bug: The agentdev-base label says that the image holds a default
policy](bugs/base-image-label-names-a-policy.md)

[Bug: the Coder start configures the git credential helper without a wait for
the keyring](bugs/coder-start-does-not-wait-for-keyring.md)

[Bug: the consumption guide does not give each template path a
class](bugs/consumption-guide-classifies-no-path.md)

[Bug: the consumption guide leaves references to deleted publisher
source](bugs/consumption-guide-keeps-publisher-source-references.md)

[Bug: the consumption guide's custom-image choices do not include the runtime
package input](bugs/custom-image-bundle-misses-runtime-inputs.md)

[Bug: firewalled Docker Hub pulls fail at the CloudFront
CDN](bugs/firewall-docker-hub-cloudfront.md)

[Bug: the enabled firewall leaves IPv6 open when `ip6tables` is
missing](bugs/firewall-ipv6-open-without-ip6tables.md)

[Bug: the base image writes the fish `PATH` setup into the build user's
home](bugs/fish-path-setup-in-build-user-home.md)

[Bug: the git-commit skill's detached-`HEAD` refusal names no
skill](bugs/git-commit-detached-head-names-no-skill.md)

[Bug: a git-new-branch hint puts the remote name into a command line without
quotes](bugs/git-new-branch-hint-unquoted-remote.md)

[Bug: Nothing runs `zsh -n` on the macOS bootstrap that shellcheck
skips](bugs/macos-bootstrap-not-syntax-checked.md)

[Bug: a merge commit skips `end-of-file-fixer` and
`trailing-whitespace`](bugs/merge-commit-skips-two-hooks.md)

[Bug: The README says that the containers do not enable
self-improve](bugs/readme-says-self-improve-not-enabled.md)

[Bug: Remote Control sessions on a workspace receive cloud-session
instructions](bugs/remote-control-sessions-get-cloud-prompt.md)

[Bug: Renovate's post-upgrade file filters do not include the runtime package's
lock file](bugs/renovate-file-filters-omit-runtime-lock.md)

[Bug: a deploy runtime that reuses a checkout does not configure the git
credential helper](bugs/reused-checkout-gets-no-credential-helper.md)

[Bug: the root-test launcher guard against unmarked tests cannot
operate](bugs/root-test-guard-cannot-fire.md)

[Bug: the runtime package installs two dependencies from a version
range](bugs/runtime-dependencies-not-pinned.md)

[Bug: the self-improve allowlist accepts a rule at any depth below
`rules/`](bugs/self-improve-allowlist-accepts-nested-rules.md)

[Reviewer decline asymmetry](bugs/self-improve-reviewer-decline-asymmetry.md)

[Unstageable routing option in the improve
skill](bugs/self-improve-unstageable-routing-option.md)

[Bug: the ASD-STE100 audit gives different findings for the same
text](bugs/ste100-audit-not-deterministic.md)

[Bug: the promote step can move the `ubuntu-ansible` tags to an older
image](bugs/ubuntu-ansible-tags-can-move-backwards.md)
