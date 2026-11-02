# Handoff: autonomous IWE loop with a fixed list of escalation triggers

Session: "agent-dev1 Autonomy rules" (explore mode, `/agentdev:iwe-explore`). Nothing was
written to the repo; this file is the only record. Status: **exploring**, not settled, no
capture made, no plan handed off.

## 1. What the user wants (read this first)

- **Goal:** a more autonomous Plan → Implement → Verify → Ship loop that makes the right
  decision on its own and has clear escalation rules for involving a human.
- **User guidance given during the session (binding):**
  - Involve the human only when truly necessary. **But do NOT put that phrasing (or my "a
    person is needed only when…" test sentence) into any rule verbatim** — it was a target
    for exploration. Design concrete, checkable rules that approximate the behaviour.
  - Wanted the proposal in **human-readable format** (plain language, no file paths in the
    proposal body), plus the list of open questions.
  - Asked to fold in the "verify is adding scope" issue (§4) and PR #587 (§6).
  - An exec summary was produced once (150-200 words, non-technical) — format accepted.
- Next: "we are about to investigate more". Expect the user to pick open questions (§8) one
  at a time (main now has "Explore settles open questions one at a time", #632 — read the
  current `iwe-explore/SKILL.md` before continuing; it changed).

## 2. Repo drift — re-verify before citing anything

All line anchors below were verified at `c96e1ef1` (2026-10-31). On 2026-11-02 `origin/main`
is `af9b9b15`, and these changed since: `iwe-shipper` (large), `iwe-verifier`,
`iwe-implementer`, `iwe-planner`, `iwe-explore`, `iwe-implement-all`, the three architecture
docs, and the off-bash plan. Known changes:

- **#616 "Conflict-free knowledge layout"**: work-item state lives only in frontmatter
  (`stage`, `rank`, `released`). Ship/cancel now write **frontmatter only** — no hub, no
  release page, no log. The release cut (`release <X.Y.Z>`) is the only writer of release
  pages and `data/log.md`, and it reads each done plan's `release` list. Active plans are
  ordered by `rank`. → Affects proposal rule 17 (Ship's owned paths shrink to: the plan,
  docs its `release` lists, specs in `## Spec changes`) and rule 16 (release derivation now
  feeds the cut, not an unreleased page).
- **Codex appears removed** (`agents/openai.yaml` files deleted; `20261031-remove-codex`
  plan exists). Three-harness constraints are now Claude Code + OpenCode; the leaf rule is
  still needed for OpenCode (`nested-subagent-dispatch.md`).
- **Off-bash plan shipped**: `stage: done`, `completed: 2026-10-31`, `released: 2.0.0`. Its
  firewall requirement was revised (on main, plan lines ~315-321, ~890-912) to "a set
  `FIREWALL_ALLOWLIST` names the allowlist in both profiles". The motivating blocker was
  resolved manually via Plan revise.
- Not yet checked on main: whether `iwe-implementer` loop step 2 ("every WARNING whose
  recommendation names a concrete route") and the evaluator rubric still read as below.

## 3. Motivating case 1 — Ship blocked on intent (firewall)

Facts (verified at `c96e1ef1`):

- Plan `data/plans/20261029-off-bash-migration`, `## Approach` (~:104-106): "Behaviour behind
  each command is unchanged; this plan changes language and packaging, not policy, so every
  existing scenario in the affected specs holds as written."
- Its MODIFIED requirement (~:838-844) and Task text (~:295-298) said only the deploy profile
  reads `FIREWALL_ALLOWLIST`. No recorded decision in Context mentioned it.
- Code `py_packages/agentdev_runtime/agentdev_runtime/firewall.py:97-105` (`allowlist_path`)
  honours `FIREWALL_ALLOWLIST` first in both profiles; old
  `init-firewall.sh:14` at `c96e1ef1^` did the same:
  `ALLOWLIST="${FIREWALL_ALLOWLIST:-${DEV_WORKSPACE_FOLDER:-/workspaces}/.devcontainer/firewall-allowlist.txt}"`.
- So: the plan contradicted **itself** (tier 3 vs tiers 4-5); code + pre-change behaviour
  followed tier 3.
- Verify missed it: Verify checks a requirement's behaviour **exists**, not that a
  **restriction** ("only deploy") holds. Only Ship's careful spec merge (steps 4-5) checks
  every SHALL clause — the one stage that cannot revise.
- The user had put the fix in the `/agentdev:iwe-ship` request; Ship couldn't use it
  (approvals apply only to commands; Ship "never edits the intent to match the code").

Conclusions reached on the original 6 questions:

- Porting Implement's evaluator loop into Ship is the **wrong tool**. Evaluator rubric
  (`iwe-revision-evaluator.agent.md:42-65`) REJECTs "requirement restated to match what was
  built" and ESCALATEs any `release` change — so every Ship intent-blocker class is
  REJECT/ESCALATE. Implement's loop works because a revision is followed by _building_; Ship
  can only merge, so any revision it could act on fits the contract to existing code.
- Revising inside `iwe-shipper` breaks Verify independence (Shipper runs Verify in its own
  context, not fresh — `fresh-context-verify.md`) and the leaf rule; a plan-only commit also
  moves HEAD → saved Verify report misses → full re-verify.
- The revise→re-ship loop already exists: `iwe-planner` step 8 re-dispatches `iwe-shipper`.
- Lighter alternative proposed: Ship blocker report carries a ready-to-run
  `/agentdev:iwe-plan revise` with the user's quoted approval; `iwe-ship` skill could offer to
  run it in place (user is present, so no evaluator needed).
- Then superseded by the bigger design (§5): fix it upstream (Verify restriction check +
  authority order in the Implement loop) so Ship stays a pure gate.

## 4. Motivating case 2 — "verify is adding scope"

Source: peer session "agent-dev1 verify is adding scope", transcript
`/root/.claude/projects/-workspaces-agent-devcontainer--claude-worktrees-bridge-cse-01Q7BhLrz1NgCRF4x3XJPhHD/bd872eec-dd9d-5686-bf78-e452931722da.jsonl`
(same off-bash plan, ship iteration, PR #591 branch `iwe/off-bash-migration/iter-2-ship`).

Its findings (claims checked against rulebooks at `c96e1ef1`):

- **Ratchet:** each fix wrote a stronger promise into the spec (one-line integrity outcome →
  full delta "refuses when a file is changed, missing, or added"); each fresh Verify then
  attacked the new promise (round 2: delete METADATA; round 3: delete whole `.dist-info`).
- **Warnings become work:** loop acts on "every CRITICAL, and every WARNING whose
  recommendation names a concrete route" (`iwe-implementer.agent.md:144-145`); Verify
  almost always names a route. Verify flags SHALL divergence and untested scenarios as
  WARNINGs (`iwe-verifier.agent.md:88-98`).
- **No baseline anywhere:** grep for pre-existing/baseline/introduced/base commit in
  verifier, implementer, evaluator → nothing. Half the blockers were faithful ports of old
  behaviour (doctor mcp-gateway/git-user checks → user chose new Task 21; integrity bypass
  limit already in bash manifest).
- Fresh context each round samples new angles → no convergence; only the 3-round bound
  stopped it.
- Open question that session raised: is Verify meant to be adversarial (security-review
  style) or a plan-vs-code conformance check? Rules say the latter.

Shared root cause with case 1: **the loop has no notion of baseline** and no brake on
self-added promises. Scope control is a precondition for autonomy.

## 5. The proposal as it stood (human-readable version shown to user)

Principle shift: replace the open-ended "material" test with a **closed list of stop
triggers**; everything else the loop decides by rule, records, and continues; judge against
the plan's promises **and the baseline**; anything outside promises is filed, never worked.

Decision rules:

1. **Authority order** (high→low): approved wording; recorded decision; Context/Approach
   intent; Spec-changes requirements/scenarios; task text; anchors/files/verification. A
   conflict resolves toward the higher tier when that tier's line, at HEAD, speaks directly to
   the point; cite both lines.
2. **No self-authorization:** a revision may cite only text present in `git show HEAD:<plan>`.
3. **Baseline:** each plan has one (state of main when its first impl branch started —
   exact definition open); every finding labelled _introduced_ vs _already there_.
4. **Preserve when silent:** if no tier speaks, take the option that removes no baseline
   behaviour and weakens no tier 1-4 line (evidence = code/test at baseline).
5. **Mark decisions/approvals** (fenced approved wording exists; propose e.g.
   `### Decision:` under Context) so "changes a person's words" is a textual diff check.

Scope rules: 6. **Pre-existing problems are filed, not worked:** a finding on behaviour the plan didn't
promise to change and that existed at baseline never blocks, never becomes a task → filed
via `/agentdev:iwe-capture` (bug/task); run continues. 7. **Only CRITICALs create work automatically;** a WARNING is fixed only if the fix fits an
existing task and adds no promise; else filed. 8. **No promise ratchet:** a revision may add a task needed to deliver an already-stated
outcome; it may not add or sharpen a claim the code must newly satisfy. Evaluator REJECTs
that; the claim is filed. (Changes the evaluator's APPROVE list: "added requirement",
"heavier Spec-changes form" only when restating what tier 3 already promised.) 9. **Later Verify rounds are delta-scoped:** round 1 full; later rounds check only prior
findings' fixes + diff since last round. New angles on unchanged code are filed. 10. **Restriction checks ("only"/"never"/SHALL NOT) only for restrictions the plan
introduces or changes vs baseline** — still catches the firewall case. 11. **Promises state their limits** at plan time (e.g. an integrity self-check can't stop a
hostile derived image), so Verify can't treat the limit as a defect.

Stop triggers (closed list) — ask a person only when:

- T1 diff touches approved wording or a marked decision;
- T2 a revision removes/weakens a SHALL, scenario, or task outcome with no tier 1-3 support;
- T3 neither rule 1 nor rule 4 resolves the conflict;
- T4 a command with effects beyond the working tree not covered by a standing approval;
- T5 a finding _introduced by this plan_ survives the whole strategy ladder.
  Mapping: Implement step 7 always-escalate → T1/T2; evaluator ESCALATE → T1/T2; Ship intent
  blocker → rules 1/4 else T3; Verify `Needs decision` → T4; stop bounds → T5.

After a trigger / process rules: 12. **Pause the smallest unit** (task → plan); independent work continues; one batched report. 13. **Strategy ladder** per recurring finding, each once: fix → different fix from a fresh
Implementer told what failed → revision under rules 1/4 → pause. 14. **Questions arrive ready to answer:** trigger, conflicting lines, drafted resolution, exact
approval phrase. No timeout defaults. 15. **Standing approvals** at plan time (command patterns, e.g. e2e, push to own
`iwe/<slug>/*` branches); T4 fires only outside them. 16. **Derive `release`:** exactly one linked feature/bug → list it; none + Spec changes `None`
→ `internal`; else T3. Contradicts `iwe-shipper` "never chooses the release impact". 17. **Ship cleans only its own leftovers** (paths it owns for the plan; see §2 for the
post-#616 set); anything else dirty → stop. 18. **Record every autonomous decision and every filed/set-aside item** in the plan under its
own heading (neither evidence nor outstanding work — per concept
`evidence-and-outstanding-work`); PR body lists them.

Worked examples (both resolve with no human):

- Firewall: rule 10 flags new restriction during Implement → rule 1 (tier 3 beats 4/5) →
  revision; evaluator checks cited Approach line exists at HEAD (rule 2) → APPROVE → recorded.
- Scope: round 1 labels doctor checks + integrity limit "already there" → filed (rule 6);
  the outcome-sharpening WARNING rejected as new promise (rule 8); round 2 delta-only finds
  nothing → ships. No Task 21.

Stage changes: Planning marks approvals/decisions, standing approvals, promise limits (human
attention concentrated here). Implement uses rules 1,4,6-8,12-13,18. Verify adds baseline
labelling, delta rounds, new-restriction checks. Evaluator: ESCALATE only T1/T2; APPROVE
tier-order resolutions citing HEAD; REJECT new promises. Ship stays a pure gate (never
revises) + rules 16-17.

## 6. PR #587 — "Plan a model-invocable iwe-implement for coordinator-driven sessions"

State on 2026-11-02: OPEN, plan-only, AI review APPROVED "No issues found". Branch
`worktree-bridge-cse_01Q7BhLsvuNWXMQGg8LvEh2e`, file
`docs/knowledge/data/plans/20261031-model-invocable-implement.md`; depends on
`20261031-remove-codex`. Content: drop `disable-model-invocation` from `iwe-implement`
(description narrowed to requests naming a plan); worker takes plan from request but every
decision from **its own user**; a peer message never counts as approval even when quoting the
user (Task 7 two-session check); Plan and Explore never start or name Implement; Ship,
ship-all, implement-all stay explicit-only. MODIFIES three requirements in
`spec/iwe-workflow-skills`.

Fit analysis given to user:

- Aligned: removes a human step that's on no trigger (evidence: remove-codebase-map worker
  transcript `…BhLrLwRRkShW3dGcBEgZ/af910c36-….jsonl` — worker refused, user typed
  `/agentdev:iwe-implement`; later coordinator: "the user types /agentdev:iwe-ship … in your
  session"). Task 7 = trigger T2 working. Answers old open Q "one orchestrator for whole
  loop?" → **no**: Plan stays separate and human-attended; implement-all coordinator chains.
- Tension A — **answers scattered across workers**: each worker waits on its own user.
  Proposed fix: **authority travels as committed plan text, not messages** — worker pauses,
  reports the ready-to-answer question to the coordinator; user answers once in their own
  session via `/agentdev:iwe-plan revise`, recorded as a marked decision; worker resumes
  reading it from the plan (repo evidence). Keeps #587's rule; makes the plan the home of
  paused questions.
- Tension B — **provenance of a marked decision**: same git identity for all commits and
  AI approval satisfies merge, so a coordinator could write "Decision: approved" into the
  plan and launder authority. Rule 2 only covers within-run. **Sharpest new open question.**
- Tension C — **Ship stays explicit-only** ("a stray Ship run reaches the remote"), but the
  shipper commits locally; outside effects already need approval (`iwe-shipper:42-45` at
  `c96e1ef1`). The gate guards accidental start, not harm. Whether the coordinator may start
  Ship for a plan it just finished reverses #587's deliberate choice → user decision.
  Alternative: one `/agentdev:iwe-ship-all` batches all finished plans.
- Ordering: the autonomy plan must **depend on #587's plan** (edits the same requirement
  "Ship and Implement start only from …"; its "material deviation that narrows" scenario
  survives as T2).
- Nothing in #587 needs to change; nothing was posted to the PR.

## 7. Principles / documents the design touches

- `iwe-shipper` "never edits the intent to match the code" — preserved (Ship still never
  revises).
- `iwe-shipper` "never chooses the release impact" — **contradicted by rule 16.**
- Implement step 7 always-escalate list — narrowed to T1/T2 (+ release only when not derivable).
- Evaluator "judge the diff, not the intent claimed" — preserved via rule 2.
- `architecture/autonomous-implement-loop.md` (leaf rule, draft→audit→evaluate→commit,
  bounds) — extended, not contradicted.
- `architecture/explicit-only-workflow-agents.md` — any new Ship caller must be added
  deliberately (PR #587 also revises this doc).
- `architecture/fresh-context-verify.md` — saved report keyed by HEAD; delta rounds keep a
  fresh context but fix its focus.
- `someday/revision-evaluator-calibration` — rules 1 and 8 add two judgment calls ("speaks
  directly to the point", "adds a new promise"); a rulebook change to the evaluator meets its
  promotion criterion; firewall plan is a first corpus entry.
- `concept/evidence-and-outstanding-work` — autonomous decisions get their own heading.
- Repo `AGENTS.md`: "Do not build instrumentation for a question nobody has framed" —
  calibration now has a framed hypothesis.

## 8. Open questions (priority order)

1. **Verify: conformance check or adversarial review?** Proposal assumes conformance;
   adversarial probing becomes separate opt-in review.
2. **What exactly is the baseline?** main at first impl branch start (stable, but other
   merged work may change behaviour) vs plan's creation commit (earlier, staler).
3. **Provenance of marked decisions** (from #587 tension B): human-approved merge only?
   signed commits? only the user's Plan session may write them?
4. **Human gate before main?** AI approval satisfies the one-approval ruleset (`cee16e2d`)
   and `pr-merge` merges → recorded decisions may never be read. Options: human approval
   only for PRs carrying contract-changing autonomous decisions, or no gate + sampled audit.
5. Should "already there" findings be filed automatically (backlog flood?) — threshold?
6. Should a WARNING ever create work automatically (only-if-fits-existing-task vs never)?
7. Is the authority order right (broad tier-3 "unchanged" beat a specific requirement)?
8. How much does untested baseline code count as evidence?
9. Where do standing approvals live (per-plan frontmatter vs repo policy) and who adds them?
10. Decision marker format; any existing convention?
11. Should Ship/release cut derive `release` (reverses an existing rule)? Re-check against
    post-#616 release-cut design first.
12. May the coordinator start Ship for a plan it just finished (reverses #587's choice), or
    batch via `/agentdev:iwe-ship-all`?
13. Plan as the durable home of paused questions?
14. Is the fresh-Implementer retry worth its cost; should cost be a stop trigger?
15. Unforeseen situations default to "loop decides" — acceptable?

## 9. Suggested next steps

- Re-read on current main: `iwe-implementer` (loop + step 7), `iwe-verifier`,
  `iwe-revision-evaluator`, `iwe-shipper`, `iwe-explore/SKILL.md` (one-question-at-a-time
  rule from #632), `architecture/autonomous-implement-loop.md`,
  `architecture/explicit-only-workflow-agents.md`. Refresh anchors.
- Check whether PR #587 merged and whether `20261031-remove-codex` shipped.
- Settle open questions 1-3 with the user, one at a time (AskUserQuestion).
- Then offer capture: `data/architecture/autonomous-escalation-rules.md` (decision + rejected
  alternatives: evaluator-gated revision inside Ship; loop in `iwe-ship-all`; open-ended
  "material" test; approval-as-scope evaluator; peer messages as approval channel) linked
  from `data/architecture.md`, or hand off to `/agentdev:iwe-plan` with dependency on
  `20261031-model-invocable-implement`. Explore hands off to Plan only (#587).
- No approved wording exists yet; nothing needs `.tmp/approved-wording-*`.

## 10. Repeat-round analysis (48h of sessions, done 2026-11-02)

Branch updated: origin/main merged into this worktree branch as `75b72ad9` (not pushed; no
upstream, no PR). Raw extraction in `.tmp/rc-scan/` (`sub-*.txt` = final reports of
iwe-verifier / iwe-revision-evaluator subagents per session; `sum.py` summarizer). Reports
were classified from their text; finding claims not re-verified in code.

Plans and rounds: ai-review-verdicts 4V (all Blocked); off-bash 5V + APPROVE/ESCALATE;
catalog-scripts-python 4V + ESCALATE; macOS-native-bootstrap 4V + APPROVE; remove-codex 3V;
okf-bundle-in-spec 3V + APPROVE; remove-codebase-map 2V + APPROVE; pre-commit 2V + ESCALATE;
kb-conflict-free-layout 1V + ESCALATE + REJECT.

Causes ranked:

- **A Evidence timing (7/9, main driver):** planner makes external-evidence tasks stand alone
  (`iwe-planner.agent.md:241-245`); verifier makes every unticked task CRITICAL
  (`iwe-verifier.agent.md:53`); loop runs Verify before PR/CI → round 1 blocked by design;
  each fix moves HEAD → cited CI stale → next CRITICAL; post-merge tasks never tickable.
- **B Warnings→work + adversarial drift (6/9):** untested scenario → new task; warning →
  sharper promise → attacked; new security angle each round (ai-review 4, off-bash 3).
- **C Main moving under parallel plans (4/9):** repo-wide grep hit another plan's file;
  remove-codex broke a command; stale map from another merge; branch carried other plan.
- **D Revision overreach (4/9):** hunks answering no finding (pre-commit 3, kb 1, macOS 1);
  some ESCALATEs correct (catalog release/decision, kb approved rank sequence).
- **E Environment-dependent verification (1/9):** doctor in bare container, xdist races.

Rule coverage: A not solved (rule 9 only partly); B largely solved by 7/8/9/11 (caveat:
plan-introduced security holes are real); C partly by 6 (+clause "other plan's change =
already there"); D partly by 1/2/8; E none.

New rules proposed: **N1** external-evidence tasks are outstanding (named closer), not
CRITICAL, inside the loop; Ship still requires them; post-merge observations leave the task
list for a post-ship check list (concept `evidence-and-outstanding-work`). **N2** batch fixes
→ push → wait CI on that head → then Verify. **N3** plan Verification commands scoped to the
plan's surface; repo-wide sweeps belong to drift audit; failures outside the surface filed.
**N4** one finding, one hunk: evaluator REJECTs unanswering hunks, drafter retries once
without them. **N5** Verification commands declare their environment; unsatisfiable ones
are outstanding, not failed.

New open question **Q16**: should "CI passes" remain a plan task, or become a Ship /
pr-merge gate (concept: "what an automated check covers, the document omits")?

## 11. Settled decisions (user)

- **Q16 settled (2026-11-02): "CI passes" is not a plan task.** User: "It is an implicit
  part of software development. There is no point of recording this in the plan."
  Consequences to carry into the plan: the planner stops writing a "CI passes" task or a
  "PR CI passes" `## Verification` line; Verify no longer raises a CRITICAL for one; the CI
  gate is owned by `pr-merge` (required checks green before every merge, impl and ship PRs).
  Aligns with concept `evidence-and-outstanding-work` ("what an automated check covers, the
  document omits"). Open plans that carry such a task (e.g. #587's
  `20261031-model-invocable-implement` Task 9) are their owners' call.
  Still open: a CI run cited as evidence for behaviour only CI can exercise (macOS job,
  image build for both architectures), and post-merge observation tasks (ai-review Tasks
  6-9) — see next question asked.
- **CI-as-behaviour-evidence (follows from Q16, user did not object):** a task may cite a CI
  job that is the only place a behaviour is exercised (e.g. macOS runner job); Verify checks
  that such a check exists and exercises the behaviour, not that it ran on the current head
  — freshness belongs to `pr-merge`. Tasks like off-bash Task 20 / okf Task 3 are "CI
  passes" in disguise and disappear.
- **Post-merge observations settled (2026-11-02): "Ship waits for them".** They stay plan
  tasks (e.g. ai-review Tasks 8-9: next Renovate PR approved and automerged; untrusted bot
  gets no approval; a person's push dismisses approval; non-blocking review approves).
  Inside the Implement loop, Verify reports them as **outstanding, not CRITICAL**, so they no
  longer force rounds; Ship's Verify requires them ticked, so "done" means seen working live.
  The plan sits implemented-but-unshipped until observed; `ship-all` skips it until then.
  Recommended alongside (not yet confirmed): at plan time prefer an automated test over an
  observation wherever one is possible; keep observations for what cannot be automated.
  Needs: a marker so Verify can tell an observation task from a normal one (e.g. the
  existing "**Closed by:** …" line, already used in off-bash Task 20).

## 12. "Prefer a test over an observation" — test families (in progress, 2026-11-02)

User: good idea but word carefully. Avoid the family of "strange tests": tests verifying
static texts, tests checking a YAML CI workflow specifies calls or a step version. Asking
for automated tests of post-merge behaviour could produce tests polling CI jobs — "way worse
than recorded observation".

Pressure source: Verify flags every untested `#### Scenario:` as WARNING
(`iwe-verifier.agent.md:92-94`) and the loop acts on WARNINGs with a route → cheapest test
for a text/YAML scenario is a content test. `test_macos_bootstrap_pins.py` added in #601
(macOS plan, 4 Verify rounds); older examples from #311/#370/#440 — habit predates the loop.

Families: (1) content tests — e.g. `scripts/tests/test_claude_remote_control_start.py:196-197`
(`'CLAUDE_CODE_OAUTH_TOKEN' not in COMPOSE.read_text()`), `scripts/tests/test_agent_runtime_ci.py:41-58`
(workflow image lines == pin), `scripts/tests/test_macos_bootstrap_pins.py` (regex on zsh vs
Ansible YAML); (2) live-system tests (poll CI/GitHub); (3) host-global-state tests — PR #637
(merged) isolated real-tmux and Xpra tests under xdist (user first cited it by mistake).
**PR #629** (merged 2026-11-01, "Run pre-commit on the rebuilt image before promotion") is the
cleanup the user meant: removed `test_pre_commit_ci_job.py`, the CI structure tests in
`test_agent_runtime_ci.py`, and YAML/string-grep assertions in paths-filter, Playwright,
preapprove, lifecycle tests ("tests that only restated workflow and action YAML"). Kept:
tests that execute logic (`test_pre_commit_ci_range.py`, paths-filter last-pass step under a
stub `gh`) and the Renovate grouping + shared-pin consistency checks. Its open Reviewer
Handoff: "Decide whether the remaining Renovate grouping and shared-pin tests ... stay or go
too" (Closed by: reviewer) == the borderline question below. No durable rule recorded the
#629 line anywhere in the graph, AGENTS.md, or rulebooks — so it can regrow.
Borderline: cross-file consistency invariants (pins agree; Renovate regex finds pin,
`scripts/tests/test_renovate_post_upgrade.py:252-264`, which runs the regex).

DRAFT wording (NOT approved yet):

- Planner: "A scenario is covered by a test only when the test runs the behaviour: it
  executes the code, script, hook, or command under test with inputs it controls, owns every
  resource it uses, and checks what results. A test that reads a repository file to check
  its text, keys, steps, or versions does not cover behaviour, and neither does one that
  queries a live service or waits on CI. Behaviour no such test can reach is an observation
  task that names who closes it, and Ship waits for it."
- Verify: "An uncovered scenario is a WARNING only when a test of that kind could cover it;
  a content check never counts as coverage."
  Pending question: cross-file consistency invariants — ban, move to lint/single source, or allow.

**Borderline settled (2026-11-02): cross-file consistency tests are out, no replacement.**
User: "there is no point in that renovate test. it only made things worse." It tests that
Renovate did its job; it does not catch proactive divergence (only if main's pin bump were
merged into the PR adding a new image use with an old pin). Incident: a new Docker-using test
raced a pin-bump PR; main landed with two different pins; main CI broke and every PR that
pulled main broke — the test blocked everyone instead of preventing the race. Note (not a
rule): the only proactive prevention is a single source — new usages read the pin file
instead of copying it. Settles #629's reviewer handoff item; leftover tests to remove later:
Renovate grouping + shared-pin tests in `scripts/tests/test_agent_runtime_ci.py`,
`scripts/tests/test_macos_bootstrap_pins.py`, `test_claude_remote_control_start.py:196-197`.

REVISED DRAFT wording (awaiting approval; supersedes the draft above):

- Planner: "A scenario is covered by a test only when the test runs the behaviour: it
  executes the code, script, hook, or command under test with inputs it controls, owns every
  resource it uses, and checks what results. These do not cover behaviour: a test that reads
  a repository file to check its text, keys, steps, or versions, or that two files agree; a
  test that checks another tool did its job; and a test that queries a live service or waits
  on CI. Behaviour no such test can reach is an observation task that names who closes it,
  and Ship waits for it."
- Verify: "An uncovered scenario is a WARNING only when a test of that kind could cover it;
  a check of file contents never counts as coverage."
- **Wording APPROVED 2026-11-02** — saved verbatim to `.tmp/approved-wording-test-coverage.md`. User also wants the tests rule in `AGENTS.md` (draft proposed, awaiting approval).
- **AGENTS.md `### Tests` added** (before `### Python Testing`), text in `.tmp/approved-wording-test-coverage.md`; committed on this worktree branch, not pushed.

## 13. Q1 settled (2026-11-02): Verify is a conformance check

User: "Verify is a conformance check. I'd move adversarial checks into its own skill. It is
good to run it for some plans. But it should be decided at plan stage as a closing task or
near closing. I'd also like to have an adversarial checks executed by plan auditor, so it
pokes for holes before plan is finalized."

Design consequences (mine, to confirm as they come up):

- Verifier rulebook: judges plan claims vs code only; no hunting for new attack angles.
- New adversarial skill (name TBD), two targets: (a) code — a plan task the planner adds
  at plan time, closing or near-closing, only for plans that warrant it; (b) plan — run at
  plan-finalization time to poke holes in the design before it is committed.
- Plan-time pass must NOT run on Implement-orchestrator revisions (planner step 7 runs on
  every revise today) — that would reintroduce the ratchet; limit to create mode and
  user-directed revise. Its findings land where humans already are (plan time) and feed
  rule 11 (promises state their limits).
- Closing-task findings: a hole that breaks a plan promise → code route (fix). The
  "introduced hole outside any promise" edge case was hypothetical — no observed finding
  fits it (ai-review holes broke stated promises; off-bash integrity limits were already
  there) — dropped from the open list on 2026-11-02. Bound: one adversarial run per plan, then conformance Verify (delta).
- Overlap to check: built-in `/security-review`, `pr-review`; existing plan-time auditor is
  only the Durable Knowledge Auditor (residue rubric) at `iwe-planner.agent.md:146-147`.
  Open: "plan auditor" = extend Durable Knowledge Auditor, or a separate fresh-context agent
  at the same step? (asked)
- **Settled (2026-11-02): a separate adversarial agent**, not an extension of the Durable
  Knowledge Auditor. **Not auto-invoked from Plan for now** — the user runs it on a plan by
  hand. User: "I am loosing track of all the possible flow loops we have now" → a loop map
  was drawn (section 14).

## 14. Loop map (drawn 2026-11-02 at the user's request)

Today — five loops: ① Verify↔code fix; ② Verify↔revision (draft → DKA → evaluator →
APPROVE commit / REJECT-ESCALATE stop); ③ PR CI + AI review ↔ fix (pr-open → pr-merge);
④ Ship CRITICAL → Implement → Ship (through the user); ⑤ Ship plan≠code → /iwe-plan revise →
re-dispatched Shipper (through the user). ①② share the bound: recurring finding, 3 Verify
rounds, 2nd revision. ③ unbounded by plan. Ship dirty worktree → user.

With decisions — [settled]: no "CI passes" task; observation tasks ("Closed by: …")
outstanding in Implement, required by Ship; tests only where they run behaviour
(AGENTS.md `### Tests`, commit 4d41be65); Verify = conformance only; adversarial review =
separate agent, a planned closing/near-closing task when chosen at plan time, and run on a
plan only by hand (Plan never invokes it); pr-merge sole CI gate. [proposed]: baseline
labels; introduced CRITICALs only drive ①; already-there / outside promises / most WARNINGs
filed; revisions by authority order, one hunk per finding, no new promises; delta rounds;
T1-T5 pause the task and batch questions; marked decisions, standing approvals, promise
limits at plan time.
Net: no new loop; ①② narrower and convergent; adversarial out of the loop into one
bounded run; ④⑤ unchanged in route, rarer in practice.

Remaining open (next up): Q2 baseline definition, Q3 decision provenance (#587), Q4 human gate
before main, and the rest of §8.
