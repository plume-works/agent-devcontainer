---
type: tracker
description: The project terms that the prose rule permits, each with its meaning.
stage: living
---

# Glossary

The prose rule in `AGENTS.md` permits a project term only if this page lists it.
Each entry is one list item: the term in bold, then `(noun)` or `(verb)`, then
the meaning in one sentence. Keep the entries in alphabetical order. Add a new
term in the same change that first uses it.

- **acceptance** (noun): The test jobs that must pass before CI promotes a
  candidate image: the deploy and Dev Container tests on each architecture, and
  the pre-commit run.
- **accepted review** (noun): A review by the AI reviewer app, in the state
  approved, changes requested, or commented, on a commit of the pull request.
- **active plan** (noun): A plan that has no `stage` field in its frontmatter.
- **agent policy** (noun): The values that the runtime writes into the OpenCode
  configuration of the user at each start.
- **agent proxy** (noun): The local HTTPS proxy of a cloud session, which adds
  GitHub credentials and limits access to the repositories of the session.
- **agent start** (noun): The command `agentdev-runtime coder start`, which the
  Coder template runs each time the Coder agent starts.
- **allowlist** (noun): The file of domain names and the optional `github-meta`
  entry, whose IPv4 addresses the firewall permits for outgoing traffic.
- **anchor** (noun): A name for a place in a file, such as `path::symbol` or
  `path#heading-slug`, that does not use a line number.
- **attach phase** (noun): The Dev Container lifecycle command
  `agentdev-runtime lifecycle attached`, which runs each time an editor attaches
  to the container.
- **auth volume** (noun): The Docker volume that holds only the Claude
  credentials, which all Dev Container instances of one host user share.
- **base** (noun): The remote branch that a work branch starts from and merges
  to stay current, `origin/main` by default.
- **base branch** (noun): The branch that the `paths-filter` action uses as the
  push target, `main` by default.
- **bootstrap transaction** (noun): The staging directory `.iwe-bootstrap.txn/`
  in the target root, which a later `iwe-bootstrap` run completes or discards.
- **bottom** (noun): The pull request of a chain that has `main` as its base.
- **bounded wait** (noun): A poll of fixed length that repeats until the GitHub
  state changes.
- **bridge plugin** (noun): Another name for the OpenCode bridge.
- **build order** (noun): The sequence of active plans, open bugs, and pending
  tasks, from the lowest `rank` to the highest.
- **candidate** (noun): In image publishing, an image that a CI run built and
  published by digest before acceptance.
- **candidate** (noun): In self-improve, a validated reviewer result that the
  foreground session routes and that changes nothing by itself.
- **carry** (verb): To keep uncommitted and untracked changes in the working
  tree when `git-new-branch` switches to the new branch.
- **catalog** (noun): The `.agents/plugins/agentdev/` tree of skills, agents,
  and scripts that Claude Code and OpenCode both load.
- **catalog entry file** (noun): A `SKILL.md`, `*.agent.md`, or `*.prompt.md`
  file that `validate_agent_files` finds.
- **catalog root** (noun): A directory that holds
  `.claude-plugin/marketplace.json` and the OpenCode bridge, which
  `agentdev-runtime catalog install` can register.
- **catalog script** (noun): A file in the `bin/` directory of the agentdev
  plugin or in the `agent-code/` directory of a skill, which an agent or a user
  runs.
- **chain** (noun): A set of dependent pull requests, from a top pull request
  down to the pull request that has `main` as its base.
- **claim** (verb): To give an empty mount root to the runtime account, and to
  refuse a mount root that has content and that another UID owns.
- **Closed by line** (noun): A `**Closed by:**` line on an unticked plan task,
  which names who or what closes the task outside the session tests.
- **cloud session** (noun): A Claude Code session that runs on a hosted machine
  and not on the computer of the user.
- **Coder user secret** (noun): A value for one user, such as `GITHUB_TOKEN`,
  that Coder puts only in the environment of its agent.
- **complete catalog** (noun): A catalog root that holds the manifests of both
  clients, so that it can replace the staged catalog.
- **consumer** (noun): A repository that adopted this template or that uses the
  agentdev images for its own project.
- **cooldown** (noun): The time that a push to `main` waits in a job that CI can
  cancel, so that many merges cause only one build.
- **core path** (noun): The steps that run before OpenCode starts: the root
  bootstrap, D-Bus, the keyring, and the `prepare` one-shot phase.
- **core service** (noun): A service of the standalone runtime whose failure
  latches the runtime, such as `dbus`, `keyring`, `prepare`, or `opencode`.
- **create phase** (noun): The one-shot program
  `agentdev-runtime lifecycle created`, which the supervisor runs one time for
  each container while `postCreateCommand` waits.
- **credential helper** (noun): The program that git asks for HTTPS credentials.
- **default branch** (noun): The main branch of a repository: `main`, `master`,
  the branch that `refs/remotes/<remote>/HEAD` names, or the branch that GitHub
  reports.
- **degrade** (verb): To continue to serve OpenCode after an optional service
  fails, with the container health set to unhealthy.
- **dependent pull request** (noun): A pull request whose base is the head
  branch of another open pull request and not `main`.
- **Depends-on trailer** (noun): A `Depends-on: #<P>` trailer on an empty
  commit, which names a pull request that the branch depends on.
- **deploy runtime** (noun): Another name for the standalone runtime.
- **derived files** (noun): The checksums, lock files, and pre-commit changes
  that a version update causes and that Renovate must commit with the update.
- **Dev Container engine** (noun): The nested `dockerd` that the
  `agentdev-devcontainer` runtime supervises in the container.
- **dispatched subagent** (noun): A catalog agent that starts in a new context
  through the Agent tool and has only the tools that its `tools:` frontmatter
  lists.
- **disposable volume** (noun): A Docker volume whose name matches
  `docker.py::DISPOSABLE_VOLUME`, which is the only type of volume that a
  garbage collection pass can remove.
- **durable-knowledge pass** (noun): The pass of a pull request review that runs
  `/agentdev:iwe-audit` on the changed docs and skills files.
- **ecosystem** (noun): In `validate_agent_files`, the marketplace and plugin
  manifest locations of one agent client, `claude` or `codex`.
- **edit cutoff** (noun): The later time of the last description edit and the
  last title change, after which a review run must start to count.
- **effective contract** (noun): The durable spec plus the intent in the
  `## Spec changes` section of a plan, which Verify compares with the code
  before Ship.
- **effort tier** (noun): The `light` or `full` setting of a pull request
  review, which controls how many passes run and which model each slot uses.
- **evidence line** (noun): The indented `- **Evidence:**` item under a ticked
  plan task, which says what was done and how it was checked.
- **excluded-directory set** (noun): The directory names that agent file
  discovery skips outside a git work tree.
- **explicit-only skill** (noun): A skill whose frontmatter sets
  `disable-model-invocation: true`, so that only the user can start it.
- **fast-approve** (verb): To approve a pull request without review passes, when
  the diff changes only versions or generated files.
- **fingerprint** (noun): A normalized hash of a lesson and its destination,
  which self-improve keeps to stop a lesson that was accepted or rejected
  before.
- **full access** (noun): The user-level OpenCode permission `"*": "allow"`,
  which the devcontainer sets by policy.
- **full adoption** (noun): The use of the whole template through
  `/agentdev:template-consume`, and not only of the published image.
- **gate** (noun): In self-improve, the check without a model that decides if a
  completed turn gets one reviewer call.
- **gate-only run** (noun): The workflow run that a push to a reviewed pull
  request starts, in which the responder check does not run.
- **global-only option** (noun): A Renovate option that only the global
  configuration of the self-hosted bot accepts.
- **harness** (noun): An agent client that the images install and that the
  catalog registers with: Claude Code or OpenCode.
- **home volume** (noun): The Docker volume `agentdev-home-${devcontainerId}`,
  one for each Dev Container instance, mounted at `/home/agent`.
- **hook directory** (noun): A directory under `/etc/agentdev/hooks/` that holds
  executables that run in C-locale order at the end of a lifecycle phase.
- **image family** (noun): The four images that one CI run builds:
  `ubuntu-ansible`, `agentdev-base`, `agentdev-deploy`, and
  `agentdev-devcontainer`.
- **image-owned path** (noun): The directory `/opt/playwright`, outside all home
  volumes, that holds the Chromium of the image.
- **immutable commit tag** (noun): The `sha-<commit>` image tag that CI
  publishes a candidate under and never moves.
- **Implement** (noun): The workflow phase that does the tasks of a plan,
  through `/agentdev:iwe-implement`.
- **Implement session** (noun): The session that loaded
  `/agentdev:iwe-implement` and follows the `iwe-implementer` rulebook, which
  takes decisions only from its own user.
- **instance** (noun): One Dev Container of one checkout or worktree.
- **iteration** (noun): The number `N` in a plan work branch name, which counts
  the work branches of the plan in all phases.
- **kept image** (noun): An image that a Docker garbage collection pass does not
  remove.
- **keyring session** (noun): The environment in `AGENTDEV_KEYRING_ENV_FILE`
  that lets a process use the supervised GNOME Keyring.
- **last passing run** (noun): The head commit of the last successful push run
  of a workflow on the base branch.
- **latch** (verb): To put the standalone runtime in its `failed` state, in
  which OpenCode stops and nothing restarts until an operator runs
  `agentdev-runtime supervisor retry`.
- **latched failure** (noun): A failure that the runtime controller cannot
  recover from.
- **lifecycle-neutral image** (noun): The `agentdev-base` image, which has the
  tools and the staged catalog but no runtime package, supervisor, or lifecycle
  commands.
- **live anchor** (noun): An anchor that the anchor check resolves: in the
  `## Key references` of an active plan, an open bug or task, or a guide.
- **local remapping** (noun): The selection of a different local port by VS Code
  for a forwarded container port when the preferred port is in use.
- **login volume** (noun): A Docker volume that holds agent credentials and that
  Docker garbage collection never removes.
- **machine position** (noun): A line number that a tool needs, such as the
  `line` field of a GitHub inline review comment.
- **managed destinations** (noun): The two trees that `iwe-bootstrap` owns in a
  target root: `.iwe` and `docs/knowledge`.
- **managed keys** (noun): The OpenCode configuration keys whose values the
  runtime writes again at each start.
- **mapped tool** (noun): The OpenCode permission or action that the bridge
  plugin uses for a Claude tool name in the `tools:` list of an agent.
- **marker** (noun): The `template-consume` section of the root
  `.agent.metadata.json` of a consumer, which records the template state.
- **marker block** (noun): The block of `PATH` lines that the macOS bootstrap
  script owns in the shell profile files.
- **merge record** (noun): The line that replaces a `## Depends on` entry after
  its pull request merges.
- **merge state** (noun): The `mergeable` and `mergeStateStatus` fields that
  GitHub reports for a pull request.
- **merge-conflict step** (noun): The first check of the
  `pr-feedback-resolution` workflow, which merges the base before a feedback
  edit.
- **metadata gate** (noun): The check of the pull request title and description
  against the diff, which stops the review with a change request before the
  passes.
- **model-invocable skill** (noun): A skill that a session can load without a
  command from the user.
- **monitoring loop** (noun): The cycle of `pr-merge` that refreshes, waits, and
  repairs until the pull request merges.
- **moving tag** (noun): An image tag that CI moves at each event, such as
  `edge`, `pr-N`, a branch name, or a semver tag.
- **namespaced command** (noun): The slash command `agentdev:<skill-name>`,
  which the bridge plugin registers in OpenCode.
- **nested container** (noun): The Dev Container that runs in the outer
  workspace.
- **newest verdict** (noun): The latest approved or changes-requested review of
  the AI reviewer, which a later commented review does not replace.
- **onboarding** (noun): The setup of a blank knowledge workspace through
  `/agentdev:iwe-setup`.
- **one-shot phase** (noun): A supervised program that runs to completion one
  time at each start: `prepare`, `config`, or `project`.
- **OpenCode bridge** (noun): The plugin at
  `.agents/plugins/agentdev/.opencode-plugin/` that makes the skills, commands,
  and agents of the catalog available in OpenCode.
- **opt-in client** (noun): A supervised program, such as OpenCode or Remote
  Control, that starts after the create phase and does not block readiness.
- **optional bundle** (noun): An opt-in group of template files that the marker
  records: `custom-image`, `knowledge-base`, or `expo`.
- **optional service** (noun): A service of the standalone runtime whose failure
  only degrades the runtime, such as `config`, `xpra`, or `dockerd`.
- **outer workspace** (noun): The Coder workspace or the host that starts the
  Dev Container.
- **outstanding observation** (noun): An unticked plan task that has a Closed by
  line, which Verify lists without a failure and Ship waits for.
- **owner** (noun): In self-improve, the existing `CLAUDE.md` file, rule, or
  skill that must hold a lesson.
- **pass** (noun): In a pull request review, one independent subagent review of
  the diff with one focus list.
- **pass** (noun): In Docker garbage collection, one run of
  `agentdev-runtime docker gc`.
- **phase** (noun): The part of the plan lifecycle that a plan work branch is
  for: `plan`, `impl`, or `ship`.
- **pin file** (noun): A file in `scripts/refresh-pin-checksums.py::PIN_FILES`
  whose downloads have a SHA-256 checksum for each architecture.
- **pin hook** (noun): The `SessionStart` hook
  `agentdev-runtime remote-control pin`, which writes the stored conversation ID
  again.
- **pinned pane** (noun): The tmux pane of session mode, which is bound to the
  stored conversation ID.
- **pins file** (noun): A Compose override file at the repository root that
  holds image references by tag and digest.
- **Plan** (noun): The workflow phase that writes a plan, through
  `/agentdev:iwe-plan`.
- **plan key** (noun): The path of a plan document relative to the knowledge
  workspace, without the extension.
- **plan state** (noun): The state of a plan that `iwe-branch-name` reads from
  the working tree: `missing`, `cancelled`, `done`, `complete`, or `incomplete`.
- **plugin cache** (noun): The directory in the home directory of the user where
  the agent client installs the plugin, and from which the scripts of the plugin
  run.
- **post-start** (noun): Another name for the start phase.
- **post-upgrade task** (noun): The one command that Renovate runs on a branch
  after its edits: `scripts/renovate-post-upgrade.py`.
- **pre-approval** (noun): The create-phase edit of the Claude state files that
  answers the onboarding, trust, Remote Control, and project MCP prompts before
  they show.
- **predecessor** (noun): The pull request that a dependent branch is based on.
- **preflight** (noun): The job of the AI review workflow that decides if a
  review runs.
- **preimage** (noun): The content hash of the target file when self-improve
  staged a proposal, which the apply step compares before it writes.
- **progress document** (noun): The file `.agentdev-template-progress.md` in a
  consumer, which holds the task list and the choices of a template setup.
- **promotion** (noun): The move of the moving tags to an accepted candidate
  digest, without a new build.
- **proposal** (noun): The new content that self-improve stages for one
  permitted target file, with an ID and a hash prefix.
- **publisher-only source** (noun): The directories `.agents/`,
  `.claude-plugin/`, and `py_packages/`, which each consumer deletes.
- **recommendation** (noun): A warning-level skill finding that shows only with
  `--recommend` and that does not change the validation result.
- **reconciliation** (noun): The decision of the user about existing state that
  `iwe-bootstrap` does not change.
- **reconnect** (verb): To merge the squash commit of a merged predecessor into
  a copy of its last head, then merge that copy into the dependent branch.
- **recorded version** (noun): The `PYTHON_VERSION` constant in the macOS
  bootstrap script.
- **recovery budget** (noun): The number of restarts that a service of the
  standalone runtime can do, with a delay that doubles after each restart.
- **refresh** (verb): To restart a client outside its recovery budget, because a
  dependency that it reads at startup recovered.
- **relay** (noun): The TCP forwarder `.claude/agent-proxy-relay.py` from the
  Docker bridge address to the port of the agent proxy.
- **release-only tools** (noun): The tools `iwe` and `iwes`, which the macOS
  bootstrap script installs from a GitHub release archive.
- **remapped account** (noun): The `agent` account of the image after the
  devcontainer CLI changes its UID and GID to those of the host user.
- **residue** (noun): In a document, text that records the path to a decision
  and not the decision, such as a list of failed attempts.
- **residue** (noun): In a pull request description, a verification that no
  automated check covers and no other document records.
- **resolver** (noun): The part of `scripts/check-anchors.py` that makes sure
  that the target of an anchor exists.
- **restack** (verb): To merge each pull request of a chain with the pull
  request below it, from the bottom to the top.
- **review responder** (noun): The `claude-respond` job, which runs Claude with
  the `pr-review` skill.
- **reviewed input** (noun): The head commit, the title, and the description
  that a review run read when it started.
- **reviewer** (noun): In self-improve, a separate `claude -p` call without
  tools that reads the evidence and returns a proposal or a discard.
- **root-test launcher** (noun): The script `scripts/run-root-tests`, which runs
  the `requires_root` tests as root.
- **rulebook followed in place** (noun): An agent definition that the session of
  a skill reads and follows itself, and does not dispatch.
- **runner job** (noun): A workflow job on a GitHub runner and not in the
  `agentdev-devcontainer` image.
- **runtime profile** (noun): The service graph that PID 1 selects through
  `AGENTDEV_RUNTIME_MODE`: `deploy` or `devcontainer`.
- **saved Verify report** (noun): The one Verify report for each plan under
  `.tmp/verify/`, which Verify uses again only when its commit is HEAD and the
  catalog did not change.
- **scaffold** (noun): The blank `.iwe/` and `docs/knowledge/` workspace in the
  `assets/` directory of `iwe-bootstrap`.
- **self-repository syntax** (noun): A `uses:` value that starts with `$/`,
  which loads an action from this repository at the current commit.
- **self-verification** (noun): The test after the firewall applies its rules,
  which makes sure that `example.com` is blocked and `api.github.com` answers.
- **server mode** (noun): The Remote Control mode in which
  `claude remote-control` runs as a server that starts a conversation on
  request.
- **session host** (noun): The machine that a cloud session runs on.
- **session mode** (noun): The default Remote Control mode, in which one tmux
  pane continues one stored conversation.
- **setup token** (noun): A `CLAUDE_CODE_OAUTH_TOKEN` login, which cannot run
  Remote Control.
- **Ship** (noun): The workflow phase that merges the spec changes of a plan and
  closes the plan, through `/agentdev:iwe-ship`.
- **Ship blocker report** (noun): The `iwe-shipper` report that starts with
  `Blocked`, changes no state, and names the skill that answers each blocker.
- **Ship records** (noun): The bug, plan, task, feature, and release documents
  that Ship leaves in the knowledge graph.
- **Ship review** (noun): The checklist section that `iwe-ship-reviewer` adds to
  a shipped plan.
- **signal** (noun): In self-improve, one of the fixed reasons that permit a
  review, such as an explicit correction.
- **slot** (noun): A role in a pull request review, such as the metadata gate or
  the correctness pass, that the effort tier gives a model.
- **slug** (noun): The file name of a plan key without its `YYYYMMDD-` prefix.
- **spawn mode** (noun): The place where a server-mode conversation runs: its
  own git worktree or the workspace directory.
- **staged catalog** (noun): The read-only copy of the catalog in the image at
  `AGENTDEV_CATALOG_DIR`.
- **stale label** (noun): A `request-ai-review` label that no unfinished review
  run on the head branch will remove.
- **standalone runtime** (noun): The `agentdev-deploy` container, whose
  supervisor prepares the workspace without the Dev Container lifecycle
  commands.
- **start phase** (noun): The Dev Container lifecycle command
  `agentdev-runtime lifecycle ready`, which runs at each container start.
- **task section** (noun): The `## Implementation Steps` section of a plan, or
  the older `## Tasks` section, where a checkbox counts as a task.
- **tense split** (noun): The rule that closed work goes under Verification and
  open work goes under Reviewer Handoff in a pull request description.
- **top** (noun): The last pull request of a chain.
- **Trigger / Path / Outcome** (noun): The three parts that each correctness
  finding of a pull request review must state, in this order.
- **trust-on-first-use** (noun): The rule that the checksum of a new version is
  the hash of its first download, which nothing else verifies.
- **trusted bot** (noun): A bot login in `TRUSTED_BOT_ACTORS`, whose pull
  requests the review app approves without a review.
- **UID/GID cohort** (noun): The project containers that run with the same
  numeric user and group IDs and that can share one auth volume.
- **umbrella** (noun): In self-improve, an owner that covers all of the class
  that a lesson belongs to.
- **update mode** (noun): In `pr-open`, a run on a branch that already has an
  open pull request.
- **update mode** (noun): In `template-consume`, the run that compares the
  template paths with the template commit that the consumer last took.
- **upstream** (noun): The tracking branch of a branch, normally
  `origin/<name>`, which is different from the base.
- **validator** (noun): The dispatch with a light model in a pull request review
  that confirms or drops each candidate finding.
- **venv root** (noun): The directory on the home volume that holds one uv
  environment for each checkout.
- **Verify** (noun): The workflow phase that compares the code with a plan
  before Ship, through `/agentdev:iwe-verify`.
- **version owner** (noun): The one place that pins the version of a pre-commit
  hook tool.
- **version-matched browser** (noun): The Chromium build that the pinned
  Playwright CLI installs, so that the client and the browser have one version.
- **work branch** (noun): A feature branch that tracks its own remote branch,
  which for a plan has the name `iwe/<slug>/iter-<N>-<phase>`.
- **worker restart** (noun): A restart of the session host that keeps the disk
  and stops all processes.
- **Workflow A** (noun): The adoption of the template through a copy of the full
  repository.
- **Workflow B** (noun): The adoption of the template through a merge into an
  existing repository.
- **workspace engine** (noun): The outer Docker engine of a Coder workspace,
  which runs the Dev Container.
- **worktree mode** (noun): The `git-new-branch` mode that creates the branch in
  a separate git worktree.
