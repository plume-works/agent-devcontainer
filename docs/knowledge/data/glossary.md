---
type: tracker
description: The shared language of the project - the terms specific to it, each with one name.
stage: living
---

# Glossary

Agent Devcontainer is a template repository that publishes container images for
AI coding agents, a catalog of skills and agents for them, and a knowledge
workflow that keeps the memory of a project in its repository.

## Language

### Distribution

**Consumer**: A repository that adopted this template or that uses the published
images for its own project. *Avoid*: Downstream, adopter, user repository

**Full adoption**: The use of the whole template, and not only of a published
image.

**Optional bundle**: An opt-in group of template files that a consumer can take
or leave.

**Progress document**: The document in a consumer that holds the task list and
the choices of a template setup or update.

**Marker**: The record in a consumer of the template commit and the optional
bundles that it took.

**Publisher-only source**: The part of this repository that exists only to
publish the catalog and the images, which each consumer deletes.

**Image family**: The set of images that one build produces and that is promoted
together.

**Candidate**: An image that a build published by digest and that has not yet
passed acceptance. *Avoid*: Release candidate, staging image

**Acceptance**: The set of tests that a candidate must pass before promotion.

**Promotion**: The move of the moving tags to an accepted candidate, without a
new build. *Avoid*: Release, publish

**Moving tag**: An image tag that points to a different image after each
promotion. *Avoid*: Floating tag, mutable tag

### Catalog

**Catalog**: The single collection of skills, agents, and scripts that every
harness loads. *Avoid*: Agent library, toolkit

**Harness**: An agent client that the images install and that the catalog
serves. *Avoid*: Agent CLI, ecosystem

**OpenCode bridge**: The adapter that makes the catalog available in OpenCode.
*Avoid*: Bridge plugin

**Staged catalog**: The read-only copy of the catalog that an image carries.

**Per-worktree catalog**: The catalog that a worktree loads from its own
checkout, so that each worktree runs the catalog of its branch.

**Rulebook**: The instructions that an agent or a skill follows. *Avoid*:
Prompt, agent definition, playbook

**Rulebook followed in place**: A rulebook that the session of a skill reads and
obeys itself. *Avoid*: Inline agent

**Dispatched subagent**: A catalog agent that starts in a fresh context with
only the tools that it declares. *Avoid*: Worker, child agent

**Explicit-only skill**: A skill that only the user can start.

**Model-invocable skill**: A skill that a session can load without a command
from the user.

### Runtime

**Runtime profile**: The set of services that a container supervises, one for
each way to run the image.

**Standalone runtime**: A container that prepares its own workspace and serves
an agent without an editor. *Avoid*: Deploy runtime

**Instance**: One Dev Container of one checkout or worktree. *Avoid*:
Environment

**Create phase**: The lifecycle phase that runs one time for each container.

**Start phase**: The lifecycle phase that runs at each container start. *Avoid*:
Post-start

**Attach phase**: The lifecycle phase that runs each time an editor attaches to
the container.

**Agent start**: The runtime step that a Coder workspace runs each time its
Coder agent starts, outside the lifecycle phases.

**Core service**: A service whose failure stops the standalone runtime.

**Optional service**: A service whose failure only degrades the standalone
runtime.

**Latched failure**: The state of a standalone runtime after a failure that it
cannot recover from, in which nothing restarts until an operator intervenes.
*Avoid*: Crash, fatal error

**Degraded runtime**: A standalone runtime that still serves its agent after an
optional service failed.

**Recovery budget**: The number of restarts that a service can use before its
failure counts.

**Opt-in client**: A supervised program that starts after the create phase and
does not block readiness.

**Watcher**: A supervised program that monitors one condition and starts a
client when the condition occurs.

**Home volume**: The storage of one instance that holds the home directory of
the agent account.

**Auth volume**: The storage that holds only agent credentials and that the
instances of one host user share.

**Login volume**: Any volume that holds agent credentials, which cleanup never
removes.

**Disposable volume**: A volume that cleanup can remove.

**UID/GID cohort**: The containers that run with the same user and group IDs and
that can share one auth volume. *Avoid*: Identity cohort

**Workspace engine**: The outer container engine, which runs the Dev Container.
*Avoid*: Host Docker

**Dev Container engine**: The container engine that runs in the Dev Container.
*Avoid*: Nested engine, inner Docker, Docker-in-Docker

**Allowlist**: The set of destinations that the firewall of a container permits
for outgoing traffic. *Avoid*: Whitelist

**Agent policy**: The harness settings that the runtime enforces at each start,
whatever the user changed.

**Pre-approval**: The answers that the runtime gives to the first-run prompts of
a harness before they show.

**Cloud session**: An agent session that runs on a hosted machine and not on the
computer of the user. *Avoid*: Remote session

**Session host**: The machine that a cloud session runs on.

**Agent proxy**: The proxy of a cloud session that adds credentials and limits
access to the repositories of the session.

### Knowledge workflow

**Knowledge base**: The memory of the project that its repository holds as
documents. *Avoid*: Wiki, docs

**Graph**: The documents of the knowledge base and the links between them.

**Scaffold**: The blank knowledge base that a consumer installs.

**Onboarding**: The setup of a blank knowledge base from the codebase of a
consumer.

**Document type**: A category of document in the knowledge base, such as a plan
or a bug.

**Work item**: A document that has a lifecycle: a plan, a bug, a release, a
backlog task, or an ADR. *Avoid*: Ticket, issue

**Reference document**: A document that has no lifecycle: a finding, a guide, or
a someday idea.

**Tracker**: A living document that sessions edit in place.

**Hub**: The list of the live documents of one type.

**Inclusion link**: A link on its own line, which makes its target a child of
the document.

**Archive**: The home of closed documents, with one folder for each release.

**Anchor**: A name for a place in a file that does not use a line number.
*Avoid*: Line reference

**Residue**: Text that records the path to a decision and not the decision.
*Avoid*: Session notes

**Build order**: The one sequence of open work, across plans, bugs, and backlog
tasks. *Avoid*: Priority list, queue

**Active plan**: A plan that is not yet closed.

**Plan key**: The name of a plan in the graph: its path in the knowledge base,
without the extension.

**Plan task**: One checkbox item of a plan. *Avoid*: Step, to-do

**Tick**: The change of a plan task from open to done.

**Completion evidence block**: The part of a commit message that says how the
agent checked the plan task that the commit ticks.

**Acceptance scenario**: A statement in a plan of one observable behaviour and
the check that proves it.

**Closed by line**: The line on an open plan task that names who or what closes
it outside the session.

**Outstanding observation**: An open plan task with a Closed by line, which Ship
waits for.

**Material deviation**: A change during Implement that affects the scope, the
behaviour, the acceptance scenarios, the ADRs, or the boundaries of the plan.

**Explore**: The workflow phase that examines a problem before a plan exists.

**Capture**: The workflow step that files a bug or a backlog task.

**Plan**: The workflow phase that writes a plan.

**Implement**: The workflow phase that does the plan tasks.

**Verify**: The workflow phase that compares the code with a plan before Ship.

**Ship**: The workflow phase that closes a plan and records what it delivered.

**Handoff**: The part of an Explore report that gives Plan the settled content
for a plan.

**Revise mode**: The Plan mode that changes an active plan.

**Ship blocker report**: The report with which Ship refuses to close a plan,
which changes no state.

**Ship review**: The checklist that a fresh context adds to a shipped plan.

**Release cut**: The step that assigns the closed documents to a version.

**Release page**: The document that says what one cut version changed.

**Work branch**: A branch that carries one piece of work and tracks its own
remote branch. *Avoid*: Feature branch, topic branch

**Iteration**: The counter of the work branches of a plan, across all phases.

### Pull requests

**Base**: The branch that a work branch starts from and merges to stay current.
*Avoid*: Parent branch, target branch

**Upstream**: The remote copy of a branch, which is different from its base.

**Chain**: A set of dependent pull requests, from the top down to the bottom.

**Dependent pull request**: A pull request whose base is the branch of another
open pull request.

**Predecessor**: The pull request that a dependent pull request is based on.
*Avoid*: Parent

**Bottom**: The pull request of a chain whose base is the main branch.

**Top**: The last pull request of a chain.

**Restack**: To bring each pull request of a chain up to date with the pull
request below it, with merges only. *Avoid*: Rebase

**Reconnect**: To join a dependent pull request to the history of a predecessor
that was squash-merged.

**Reorder pull request**: A pull request whose only change is the position of
work items in the build order.

**AI reviewer**: The bot account that submits the AI review of a pull request.
*Avoid*: Review bot, Claude reviewer

**AI review gate**: The rule set that decides if a pull request has the AI
review that it needs to merge.

**Review responder**: The automated run that reviews a pull request for the AI
reviewer.

**Trusted bot**: A bot whose pull requests are approved without a review.

**Fast-approve**: To approve a pull request without review passes, because it
changes only versions or generated files.

**Effort tier**: The depth of a pull request review, which sets how many passes
run.

**Pass**: One independent review of a diff with one focus.

**Metadata gate**: The check of the title and the description of a pull request
against its diff, which runs before the passes.

**Reviewed input**: The commit, the title, and the description that a review
read when it started.

**Newest verdict**: The latest approval or change request of the AI reviewer,
which a later comment does not replace.
