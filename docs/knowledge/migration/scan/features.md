# Feature scan

Each feature's `## Behaviour` and `## Edge cases`, split into statements and
compared with `data/spec/`. Counts are covered / unique / conflict. Paths are
under `docs/knowledge/data/`.

## Per feature

| Feature                              | Stage       | Owning specs                                                                          | Counts      |
| ------------------------------------ | ----------- | ------------------------------------------------------------------------------------- | ----------- |
| agentdev-iwe-workflow-skills         | implemented | iwe-workflow-skills, catalog-lifecycle                                                | 3 / 3 / 0   |
| agentdev-runtime-cli                 | implemented | agentdev-runtime-images, firewall, devcontainer-opencode-policy, template-consumption | 8 / 8 / 0   |
| agent-sign-in-without-seeding        | implemented | claude-remote-control                                                                 | 6 / 1 / 0   |
| ai-responder-workflows               | implemented | ai-review-gate, template-consumption                                                  | 33 / 11 / 0 |
| autonomous-implement-loop            | implemented | iwe-workflow-skills                                                                   | 13 / 0 / 1  |
| bun-only-javascript-runner           | implemented | none                                                                                  | 0 / 4 / 0   |
| catalog-installed-in-image           | implemented | catalog-lifecycle                                                                     | 9 / 3 / 1   |
| claude-and-opencode-only-harnesses   | implemented | none                                                                                  | 1 / 6 / 1   |
| claude-remote-control-resume         | implemented | claude-remote-control                                                                 | 6 / 2 / 0   |
| claude-remote-control-server-mode    | implemented | claude-remote-control                                                                 | 9 / 2 / 0   |
| cloud-session-host-toolchain         | implemented | none                                                                                  | 0 / 10 / 0  |
| coder-remote-control-autostart       | implemented | claude-remote-control, coder-ide-baseline                                             | 6 / 0 / 2   |
| codex-full-access-config             | deprecated  | none                                                                                  | 0 / 6 / 0   |
| consumer-iwe-seed                    | implemented | template-consumption, iwe-bootstrap                                                   | 17 / 1 / 0  |
| devcontainer-home-volume             | implemented | agentdev-runtime-images, catalog-lifecycle                                            | 7 / 7 / 1   |
| docker-storage-limits                | implemented | devcontainer-docker-storage                                                           | 12 / 1 / 0  |
| expo-eas-builds                      | implemented | template-consumption, coder-ide-baseline                                              | 15 / 3 / 0  |
| fresh-map-on-push                    | deprecated  | none                                                                                  | 0 / 12 / 0  |
| gitignore-aware-agent-file-discovery | implemented | agent-file-discovery                                                                  | 9 / 1 / 0   |
| git-new-branch                       | implemented | git-new-branch, iwe-workflow-skills                                                   | 11 / 0 / 0  |
| iwe-branch-name                      | implemented | iwe-branch-name, iwe-workflow-skills                                                  | 11 / 0 / 2  |
| macos-native-bootstrap               | implemented | macos-native-bootstrap                                                                | 14 / 2 / 0  |
| manual-stacked-prs                   | implemented | stacked-prs, update-branch                                                            | 17 / 2 / 0  |
| map-masks-version-bumps              | deprecated  | none                                                                                  | 0 / 13 / 0  |
| native-stacked-prs                   | deprecated  | stacked-prs, pr-merge-conflicts                                                       | 1 / 7 / 6   |
| nested-agent-dispatch                | implemented | nested-agent-dispatch, devcontainer-opencode-policy                                   | 2 / 4 / 0   |
| no-working-logbooks                  | implemented | iwe-workflow-skills                                                                   | 6 / 10 / 0  |
| opencode-catalog-host                | implemented | opencode-catalog-bridge, catalog-lifecycle, opencode-web                              | 15 / 3 / 1  |
| opencode-full-access-config          | implemented | devcontainer-opencode-policy, opencode-catalog-bridge                                 | 7 / 1 / 0   |
| opencode-web-coder-autostart         | implemented | opencode-web                                                                          | 11 / 6 / 1  |
| opencode-workspace-cbm-indexing      | deprecated  | none                                                                                  | 0 / 13 / 0  |
| persist-pre-commit-cache             | implemented | none                                                                                  | 0 / 8 / 0   |
| playwright-browser                   | implemented | playwright-browser                                                                    | 5 / 1 / 0   |
| pr-description-guidance              | implemented | template-consumption                                                                  | 10 / 4 / 0  |
| pre-commit-ci-gate                   | implemented | pre-commit-gate                                                                       | 10 / 5 / 1  |
| pre-commit-owns-formatting           | implemented | pre-commit-gate (CI statements only)                                                  | 2 / 7 / 0   |
| preserved-approved-wording           | implemented | iwe-workflow-skills                                                                   | 7 / 3 / 0   |
| pr-feedback-resolves-merge-conflicts | implemented | pr-merge-conflicts                                                                    | 6 / 0 / 0   |
| pr-review-docs-durable-knowledge     | implemented | none                                                                                  | 0 / 12 / 0  |
| pr-verification-sections             | implemented | template-consumption (two statements)                                                 | 2 / 6 / 0   |
| remote-control-environment-names     | implemented | claude-remote-control                                                                 | 7 / 3 / 0   |
| renovate-maintains-checksums         | implemented | dependency-updates, image-pinning                                                     | 4 / 6 / 1   |
| resumable-template-consumption       | implemented | template-consumption                                                                  | 7 / 0 / 0   |
| reusable-agentdev-devcontainer       | implemented | agentdev-runtime-images, catalog-lifecycle, image-pinning                             | 12 / 0 / 0  |
| risk-scaled-spec-deltas              | implemented | iwe-workflow-skills                                                                   | 7 / 5 / 0   |
| self-improve-plugin-in-catalog       | implemented | none (runtime only in self-improve-learning-loop)                                     | 0 / 8 / 0   |
| ship-review                          | implemented | iwe-workflow-skills                                                                   | 4 / 3 / 0   |
| standalone-opencode-container        | implemented | standalone-opencode-runtime, catalog-lifecycle                                        | 17 / 2 / 3  |
| standalone-remote-control-autostart  | implemented | claude-remote-control, standalone-opencode-runtime                                    | 6 / 0 / 0   |
| update-branch-pulls-upstream         | implemented | update-branch                                                                         | 5 / 1 / 0   |
| uv-run-only-environment              | implemented | agentdev-runtime-images (devcontainer half)                                           | 4 / 9 / 1   |
| verification-in-the-main-loop        | implemented | iwe-workflow-skills, plan-checkbox-evidence                                           | 10 / 0 / 1  |
| verify-report-cache                  | implemented | iwe-workflow-skills                                                                   | 10 / 1 / 0  |
| xpra-port-forwarding                 | implemented | xpra-port-forwarding                                                                  | 3 / 1 / 0   |

Totals: 637 statements, 387 covered, 227 unique, 23 conflict.

## Conflicts

Each is a feature statement a spec contradicts. The spec side is named by its
requirement.

- autonomous-implement-loop: "acts on every CRITICAL and on every WARNING that
  names a concrete route" against iwe-workflow-skills, "Implement verifies its
  own work and acts on the report".
- catalog-installed-in-image: "establishes the volume→`/root/.claude.json`
  symlink" against catalog-lifecycle, "the catalog is installed at image build
  time and again by postCreateCommand" ("SHALL be a regular file").
- coder-remote-control-autostart: "autostart is Coder-only" against
  claude-remote-control, "Remote Control autostarts only on a live claude.ai
  login".
- coder-remote-control-autostart: a `coder_script` runs
  `.devcontainer/scripts/claude-remote-control-start.sh` against
  coder-ide-baseline, "the repository ships the Coder agent-start command".
- claude-and-opencode-only-harnesses: "the shared agents-auth volume keeps
  `codex/auth.json`" against catalog-lifecycle, "only agent credentials are
  shared across worktrees".
- iwe-branch-name (two statements): the plan is "read at the fetched remote
  default branch" against iwe-branch-name, "Plan state is read in the checkout".
- devcontainer-home-volume and opencode-catalog-host: OpenCode's database on the
  home volume against opencode-web, "OpenCode logins and chats survive a
  rebuild" (a per-instance `agentdev-opencode` volume). catalog-lifecycle, "only
  agent credentials are shared across worktrees", agrees with the features; the
  opencode-web requirement is the one to check against
  `.devcontainer/docker-compose.yml`.
- opencode-web-coder-autostart: the volume "mounted at
  `/root/.local/share/opencode`" against agentdev-runtime-images, "the Dev
  Container runs as a non-root account on one home volume".
- native-stacked-prs (six statements, deprecated): `gh stack` publishing,
  merging, and rebasing against stacked-prs, "No branch is rewritten", and
  pr-merge-conflicts, "Feedback resolution resolves merge conflicts first".
- pre-commit-ci-gate: "CI runs the new binary only once the image digest bump
  merges" against pre-commit-gate, "the rebuilt image passes every hook before
  promotion".
- standalone-opencode-container: "Start OpenCode only after required services
  and matching project preparation succeed" against standalone-opencode-runtime,
  "startup prepares or reuses one workspace".
- standalone-opencode-container: "exit the container if recovery is exhausted"
  against standalone-opencode-runtime, "services have supervised bounded
  recovery".
- standalone-opencode-container: "the proxy owns Xpra access authentication"
  against standalone-opencode-runtime, "browser access uses an external proxy".
- renovate-maintains-checksums: the `agent-desktop` image name against
  image-pinning, "workflow container images share the devcontainer pin".
- uv-run-only-environment: the environment root default `/uv/venvs` against
  agentdev-runtime-images, "each checkout has its own project environment".
- verification-in-the-main-loop: "no separate persisted verification artifact is
  required" against iwe-workflow-skills, "Normal shipping requires a clean
  independent verification".

## Unique statements worth keeping

Features whose unique statements describe something still in the repository. The
statements are read from the feature when it is folded; this list says where
each feature's unique statements go.

| Feature                                                                                                                                              | Destination spec                         |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| agentdev-runtime-cli, devcontainer-home-volume, uv-run-only-environment (devcontainer half)                                                          | agentdev-runtime-images                  |
| agentdev-iwe-workflow-skills, preserved-approved-wording, risk-scaled-spec-deltas, ship-review, no-working-logbooks (auditor and harness statements) | iwe-workflow-skills                      |
| ai-responder-workflows                                                                                                                               | ai-review-gate                           |
| claude-remote-control-resume, claude-remote-control-server-mode, remote-control-environment-names                                                    | claude-remote-control                    |
| catalog-installed-in-image, opencode-catalog-host (CLI pin, one bridge entry), self-improve-plugin-in-catalog (marketplace statements)               | catalog-lifecycle                        |
| opencode-catalog-host (bridge root, no dependencies)                                                                                                 | opencode-catalog-bridge                  |
| opencode-web-coder-autostart                                                                                                                         | opencode-web                             |
| opencode-full-access-config                                                                                                                          | devcontainer-opencode-policy             |
| playwright-browser                                                                                                                                   | playwright-browser                       |
| pr-description-guidance, expo-eas-builds                                                                                                             | template-consumption                     |
| pre-commit-ci-gate, pre-commit-owns-formatting, persist-pre-commit-cache, bun-only-javascript-runner                                                 | pre-commit-gate                          |
| renovate-maintains-checksums                                                                                                                         | dependency-updates                       |
| standalone-opencode-container                                                                                                                        | standalone-opencode-runtime              |
| manual-stacked-prs                                                                                                                                   | stacked-prs                              |
| macos-native-bootstrap                                                                                                                               | macos-native-bootstrap                   |
| nested-agent-dispatch                                                                                                                                | nested-agent-dispatch                    |
| gitignore-aware-agent-file-discovery                                                                                                                 | agent-file-discovery                     |
| update-branch-pulls-upstream                                                                                                                         | update-branch                            |
| xpra-port-forwarding                                                                                                                                 | xpra-port-forwarding                     |
| verify-report-cache                                                                                                                                  | iwe-workflow-skills                      |
| no-working-logbooks (Evidence smells)                                                                                                                | plan-checkbox-evidence                   |
| self-improve-plugin-in-catalog (runtime statements)                                                                                                  | self-improve-learning-loop               |
| claude-and-opencode-only-harnesses                                                                                                                   | new `supported-harnesses`                |
| cloud-session-host-toolchain                                                                                                                         | new `cloud-session-host`                 |
| pr-review-docs-durable-knowledge, pr-verification-sections                                                                                           | new `pr-review` and new `pr-description` |
| uv-run-only-environment (CI half)                                                                                                                    | new `ci-python-environment`              |

Nothing is kept from the five deprecated features, or from statements about
removed things: the Codex Cloud bootstrap, seeding secrets, renamed operator
commands, the codebase map.
