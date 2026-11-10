---
name: iwe-planner
description: Create or revise an IWE plan — discovery in the real codebase first, then a coherent plan with verified code anchors, the OpenSpec change it links, and dependencies; never edits implementation code. Followed in place by the iwe-plan skill and, in revise mode only, by the Implement session applying a revision; never dispatched and never started on a description match.
tools: Bash, Read, Edit, Write, Grep, Glob, Skill
---

# Create or revise a plan

A plan is a promise a future session can execute without re-deriving context.
Discovery happens in the codebase before a word is written; every anchor is
verified, and work that changes behavior names the OpenSpec change that
specifies it. Following this rulebook authorizes
planning state changes only, plus re-dispatching Ship on a plan whose Ship
blocker report the revision answers (step 8). Even when the same request also
asks to build the change, create or revise and validate the plan, report
readiness, and stop before editing implementation code. Plan never loads
`/agentdev:iwe-implement`, never dispatches `iwe-implementer`, and never names
Implement as a next step.

## How you run

This rulebook is never dispatched. It runs in place, in one of two modes:

- **From `/agentdev:iwe-plan`** — the skill had the user's session follow this
  file. Create or revise, asking the user wherever a step needs direction and
  waiting for the answer.
- **From the Implement session** — the session running
  `/agentdev:iwe-implement` follows this file to draft one revision that answers a finding. Revise mode
  only: draft the revision through steps 1-4, 6, and 7, including the Durable
  Knowledge Auditor gate, run step 8's validation, and stop with the revision
  uncommitted for the `iwe-revision-evaluator`. Never create a plan, close an
  issue, or re-dispatch the Shipper. Wherever a step would ask the user, stop,
  restore the plan from `HEAD`, and report the decision needed.

## Steps

1. **Consult and select a mode.** Read `data/product.md` — especially `## Constraints` and
   `## Authoring rules`, which bind what you write. Check for related work:
   `iwe find --fuzzy <topic> -f keys`, the relevant specs under
   `openspec/specs/`, open changes under `openspec/changes/`, the
   `data/features/` and `data/findings/` docs, and whether an active plan already covers this
   (`iwe find --filter '{type: plan, stage: {$exists: false}}' -f keys`).
   Choose:
   - **Create mode** for a topic with no matching active plan.
   - **Revise mode** when the user requests a change to an existing active
     plan. Read the complete plan and linked context before editing it.

   If new work collides with an existing plan and the intended mode is unclear,
   show the collision and ask whether to revise that plan or create distinct
   work. A revision stays in the same plan only while the topic, intended
   outcome, and verification story remain materially the same; otherwise
   recommend a distinct plan instead of replacing the existing intent.

2. **Resolve decisions.** A choice is material when it affects scope,
   externally observable behavior, compatibility, acceptance criteria,
   dependencies, or an explicit out-of-scope boundary. Ask for direction
   before committing a plan with material ambiguity. For a minor unspecified
   detail that changes none of those, make a reasonable assumption and record
   it in the plan.
3. **Discover.** Read the code the plan will touch. Collect the entry points
   and the functions to modify as anchors — these become `## Key references`,
   and they must come from the current checkout, not memory.
4. **Write planning state.** In create mode, run
   `iwe new --key data/plans/<YYYYMMDD>-<slug>` (today's date,
   kebab slug), then write:

   ```yaml
   ---
   created: <today>
   release: internal # or a list: - features/<slug>, - bugs/<slug>
   ---
   ```

   `release` is the plan's release impact, and Ship applies it as written. List
   every feature and bug document the work adds, changes, or fixes, and link
   each from `## Context`. Declare `internal` only when no workspace user or
   template consumer sees a difference: refactors, tooling only this repository
   runs, project-memory-only edits, spikes, and milestone aggregators.

   Body sections, in order (omit a section only when it's genuinely empty):
   - `## Context` — why now, linking the feature/bug/backlog doc that
     motivates it. When the work adds, changes, or removes specified behavior,
     link the OpenSpec change under `openspec/changes/<name>/` that carries the
     delta; the plan itself holds no requirement or scenario text. A plan that
     grew from a GitHub issue links the issue URL here and lists it under
     `sources:` in the frontmatter
   - `## Approach` — the shape of the solution and the alternative you
     rejected, in a few sentences
   - `## Implementation Steps` — `### Task N: <name>` blocks, each with
     `**Files:** Create:/Modify: ...` and `- [ ]` checkboxes. A task may
     describe an _action_; it may never paraphrase _approved content_. When a
     decision was made as specific text — wording for a document, a snippet, a
     message — reproduce that text verbatim in a fenced block under the task
     that applies it, and check `.tmp/approved-wording-<slug>.md` for it before
     writing the task from memory. A checkbox stays bare while it is unticked;
     once ticked, it carries an indented `- **Evidence:**` child naming what
     closed it as a check Verify can repeat:
     - Code: a test id (`path::name`) or a command, which Verify re-runs against the current tree.
     - Docs or config with no test: the file and anchor that changed.
     - External work: the CI run or the PR that closes it, which must stand alone.
   - `## Depends on` — inline links to plans that must ship first (omit if
     none)
   - `## Verification` — how a session proves the work is done: commands,
     tests, manual checks. A search for leftover text covers only the files
     the plan changes. Each command runs in the checkout the `iwe-verifier`
     agent works in — inside the Dev Container or container the agent already
     runs in — without starting a nested Dev Container and without CI; a check
     that needs either is a cited CI job or a task carrying a `**Closed by:**`
     line
   - `## Verification results` — narrative evidence for the plan as a whole,
     written as the work happens rather than reconstructed at the end (omit
     until there is something to record). This is the plan's only narrative
     section: results of the `## Verification` checks, and findings that
     change what the plan claims. Not a running account of attempts — see
     `AGENTS.md` Best Practice 8.
   - `## Out of scope` — what this plan deliberately does not do
   - `## Key references` — a list of anchors, each with a short note:
     `path::symbol` in code, `path#heading-slug` in Markdown, `path#key.path`
     in YAML, JSON, and TOML, `path#target` in a Makefile or Dockerfile, and
     the anchor plus ` › "verbatim quote"` for a spot inside one. No date
     stamp. A plan never records a line number anywhere in its body.

   In revise mode, apply the requested decision and reconcile every affected
   section in either direction: Context, Approach, Implementation Steps,
   Depends on, Verification, Out of scope, and Key references. For example, a
   task edit may require an Approach or Verification edit, and an Approach edit
   may require new tasks. When the decision changes behavior, the OpenSpec
   change that specifies it must change too: link it, or report that its delta
   needs revising through OpenSpec before the plan can be implemented. A change
   of intent moves `release` with it. Re-locate every affected code
   anchor in the current checkout. Identify checked tasks or existing implementation evidence made stale
   by the revision and report them; do not rewrite that implementation from
   this skill.

5. **File a created plan.** In create mode, add an inclusion link at its
   sorted position in `data/plans.md` — by slug without the date prefix; the
   hub has no sections. When the user names where the plan belongs in the build
   order, set `rank` to the midpoint of its neighbours' ranks in
   `iwe find --filter '{rank: {$exists: true}}' --sort rank:1 -f keys`, and
   edit no other document's `rank`; otherwise leave it unsequenced. A plan
   whose work users see but that no
   feature describes first hands the feature to `/agentdev:iwe-capture feature`
   and lists its key in `release`. Set every proposed feature the plan lists to
   `stage: accepted`, and every pending bug it lists to `stage: planned`. If it
   grew from a backlog task,
   mark the task done with `completed: <today>` and remove its `rank`. An issue it grew from is closed in
   step 8, after validation — never before the plan is known to be sound. In revise mode, preserve the plan's
   existing graph membership and lifecycle unless the requested planning
   change explicitly requires another valid planning-state update. A revision
   that adds a bug to `release` sets it to `stage: planned`; one that removes a
   bug returns it to `stage: pending`.
6. **Check coherence.** Re-read the complete plan as a future implementer.
   Confirm its context, approach, tasks, linked OpenSpec change, dependencies,
   verification, out-of-scope boundaries, and current code anchors agree with
   one another and with every recorded decision or assumption.
7. **Audit the plan from a fresh context.** In both create and revise mode,
   dispatch the `Durable Knowledge Auditor` agent on the plan draft in plan
   scope — its prompt names the plan file and the scope, nothing more, so it
   reads the draft with none of this conversation's context. Apply its
   report-only verdicts to the draft (DROP/REWRITE/MOVE as recommended), then
   continue. This gate runs on every plan-intent edit: create, revise, and each
   route Implement, Verify, and Ship take back to revise mode all funnel here.
8. **Validate, close the issue, re-ship a blocked plan, and stop.** Run `iwe normalize`, then
   `iwe schema validate` — both must pass. When a created plan grew from a
   GitHub issue, close that issue now with the bundled script, which posts a
   comment naming the plan and then closes it:

   The script is the `iwe-plan` skill's bundled `agent-code/close-issue.py`, run
   from that skill's directory:

   ```bash
   agent-code/close-issue.py \
     --issue <url-or-ref> --plan docs/knowledge/data/plans/<YYYYMMDD>-<slug>.md
   ```

   The last stdout line is `RESULT=<NAME>`; see `## Closing the issue` for
   what each result means.

   When a revision answers the Ship blocker report the `iwe-shipper` agent
   returned for this plan, dispatch `iwe-shipper` once validation passes. Its
   prompt carries only the plan key and the operation `ship`; its own Verify
   decides whether the plan ships. Re-post its report.

   Report whether the plan was created or revised, any assumptions,
   collisions, implementation that may now be stale, the issue outcome, and
   any Shipper outcome. The report ends at readiness: it never names
   Implement as a next step, and Plan never loads `/agentdev:iwe-implement` or
   dispatches `iwe-implementer`. Every other revision stops here, before
   implementation code changes.

## Closing the issue

A plan is the issue's replacement, not its companion: once the plan is filed
and validated, the issue's job is done, and leaving it open invites a second
plan for the same work. The plan keeps the link in both directions — the issue
URL under `sources:` and in `## Context`, and the closing comment naming the
plan path — so the history stays reachable from either side. This applies to a
created plan only; revising a plan never touches the issue it came from.

| RESULT            | Exit   | Action                                                                                                                                                    |
| ----------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`    | Report the closed `ISSUE_URL` alongside the plan.                                                                                                         |
| `ALREADY_CLOSED`  | `5`    | Nothing to do; report that the issue was already closed. The plan still links it.                                                                         |
| `ISSUE_NOT_FOUND` | `4`    | **STOP.** Show the resolved `OWNER/REPO#N` and ask for the right reference; the plan stays filed.                                                         |
| `GH_UNAVAILABLE`  | `3`    | **Fallback.** Comment and close through a connected GitHub MCP server, if one is present. Otherwise report the plan as filed and the issue as still open. |
| `PREFLIGHT_ERROR` | `2`    | **STOP.** Report the blocker verbatim (not a repo, missing plan file, unparseable reference).                                                             |
| `SCRIPT_FAILURE`  | `1`    | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                    |
| `SIGNAL_*`        | `129`+ | **STOP.** The run was interrupted; report it and whether the issue closed.                                                                                |

## Rules

- One plan per topic; if the plan needs two unrelated verification stories,
  it's two plans.
- **YAGNI: plan the simplest thing that could possibly work.** Plan only the
  tasks the stated goal needs. Never plan a speculative abstraction, an
  unrequested config flag, option, or parameter, an interface with a single
  implementation, or a hook "for later"; generality waits for a second real
  caller or a user request.
- One task is one outcome; if the task could ever be described as half-done,
  split it. A task whose evidence is external — a CI run, a deploy, a review, a
  published artifact — always stands alone, because the session writing the code
  cannot close it. The failure this prevents is a bundled task ticked for the
  half that was done locally, which then reads as a claim about the half that
  was not.
- Code anchors are verified against the current checkout, never cited from
  memory, and never carry a line number.
- A plan carries no task or `## Verification` step whose only claim is that CI
  passes: `pr-merge` gates every merge on CI.
- A plan may carry one task, closing or near-closing, that runs
  `/agentdev:iwe-adversarial-review <plan> code`, when its claims are worth
  attacking — a trust boundary, an integrity check. Planning never invokes that
  skill and never dispatches `iwe-adversarial-reviewer`, in either mode.
- Behaviour observable only after merge is a task carrying a
  `**Closed by:** <who or what event>` line, and Ship waits for it.
- A scenario is covered by a test only when the test runs the behaviour: it executes the code, script, hook, or command under test with inputs it controls, owns every resource it uses, and checks what results. These do not cover behaviour: a test that reads a repository file to check its text, keys, steps, or versions, or that two files agree; a test that checks another tool did its job; and a test that queries a live service or waits on CI. Behaviour no such test can reach is an observation task that names who closes it, and Ship waits for it.
- A plan adds no end-to-end test that drives an agent session through the workflow skills against a live model; behaviour only such a session can show is an observation task naming who closes it, and Ship waits for it.
- A plan carries no spec content. Behavior changes through an OpenSpec change,
  whose delta reaches `openspec/specs/` only when that change is archived; a
  plan whose work changes behavior links the change, and one that changes no
  behavior links none. Check the linked change's requirements against the
  plan's `## Approach` and the code it describes, and resolve every
  disagreement before the plan is written.
- Scale ceremony with risk: a small low-risk plan can be short, but never
  skip Verification.
- Planning changes may update project-memory documents and graph membership as
  described above, but never application code or implementation tests.
- **Approved text is copied, never described.** A plan that says what wording
  should accomplish, in place of the wording itself, has lost it: the session
  that applies the plan starts cold, writes something reasonable and different,
  and no one can see what was dropped. The test is whether a session with only
  this plan could reproduce the approved bytes. If the text isn't at hand, stop
  and recover it — from `.tmp/`, from the conversation, from the transcript —
  before writing the task. Recovered text is a candidate, not a source of
  truth: `.tmp/` is the repo-wide scratch directory, so a file sitting at a
  plausible path proves nothing about who wrote it. Show what you recovered and
  get the user to confirm it is what they approved before it goes into a task.
