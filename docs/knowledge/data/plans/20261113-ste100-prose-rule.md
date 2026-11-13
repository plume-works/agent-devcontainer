---
type: plan
created: 2026-11-13
release: internal
description: Make ASD-STE100 Issue 9 a hard rule for the text that a change adds or edits, with a glossary of project terms and an audit-ste100 skill that runs before the durable-knowledge audit.
sources:
- resource: https://www.asd-ste100.org/
- resource: AGENTS.md
- resource: docs/knowledge/AGENTS.md
- resource: .agents/plugins/agentdev/skills/iwe-audit/SKILL.md
- resource: .agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: docs/spec-audit/specs.jsonl
---

# Make ASD-STE100 the rule for all prose

## Context

The repository has no rule that sets a writing standard for prose. The
repository owner decided that ASD-STE100 Issue 9 (Simplified Technical English,
released 2025-01-15) is a hard rule for all prose that agents write, and that
this rule comes before the work in [Shrink the knowledge base to an issue
tracker and decision
records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md).

The repository owner's decisions:

- The rule applies to documents under `docs/knowledge/`, skill and agent
  rulebooks, `AGENTS.md` files, READMEs, code comments, commit messages, and
  pull request titles and bodies.
- The rule applies only to the text that a change adds or edits. [Migrate
  existing prose to ASD-STE100](../backlog/migrate-prose-to-ste100.md) converts
  the earlier text.
- The rule names the issue of the standard, so that a later issue does not
  change the rule without a decision.
- A new skill, `audit-ste100`, checks the rule from a fresh context and runs
  before the Durable Knowledge Auditor.
- The skill checks from the model's own knowledge of the standard. [Full
  ASD-STE100 compliance](../someday/ste100-full-compliance.md) holds the idea of
  a check against the standard itself.
- A glossary is the list of project terms that the rule permits.
- Commit messages and pull request text follow the written rule. No audit reads
  them.

## Approach

The rule is one best practice in the root `AGENTS.md`. The knowledge-base manual
and the product page each point to it.

The glossary is one page, `docs/knowledge/data/glossary.md`. It uses the
`tracker` type, which is the type for a reference page that is edited in place.
The terms come from the `glossary_terms` that `docs/spec-audit/specs.jsonl`
holds. The `iwe-bootstrap` assets get the same schema binding and an empty
glossary, because the knowledge-base manual that they install points to it.

The skill `/agentdev:audit-ste100` reports and edits nothing. An agent,
`STE100 Auditor`, runs it from a fresh context, as the
`Durable Knowledge Auditor` agent runs `/agentdev:iwe-audit`.

The audit runs at the two places where the durable-knowledge audit runs:

- `/agentdev:iwe-plan-review` dispatches the `STE100 Auditor` first and alone.
  If it reports a finding, the skill returns only that report. The other three
  reviewers run only on a draft that has no finding.
- `/agentdev:pr-review` runs the skill on the prose that the diff adds, before
  the durable-knowledge pass.

Rejected:

- **A rule page written from the Issue 9 document.** The repository owner chose
  a less formal first version, because the standard is a 434-page document.
- **A check of each word against the ASD-STE100 dictionary.** ASD owns the
  dictionary, and a copy in the repository needs terms from ASD that permit it.
- **A pre-commit script that counts the words in a sentence.** The script must
  tell new text from old text and a procedure from a description.
- **The `STE100 Auditor` as a fourth parallel plan reviewer.** The other
  reviewers would read text that the corrections then change.
- **An audit of each commit message, or of the pull request title and body.**
  The repository owner chose the written rule alone for these.

## Implementation Steps

### Task 1: State the rule

**Files:** Modify: `AGENTS.md`, `docs/knowledge/AGENTS.md`,
`docs/knowledge/data/product.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/AGENTS.md`

- [ ] `AGENTS.md#best-practices-for-agents` holds this item after item 14, with
  the text that the repository owner approved:

  ``` markdown
  15. **Write all prose in ASD-STE100 Issue 9 (Simplified Technical
      English).** The rule applies to the text that a change adds or
      edits in these places: documents under `docs/knowledge/`, skill
      and agent rulebooks, `AGENTS.md` files, READMEs, code comments,
      commit messages, and pull request titles and bodies. Text that
      existed before this rule can stay until a change edits it.
      - Use a project term only if `docs/knowledge/data/glossary.md`
        lists it. Add a new term to the glossary in the same change.
      - Text in code formatting, text in a fenced block, and quoted
        text are not prose. The rule does not apply to them.
      - The rule names the issue. A later issue applies only after
        this rule names it.
      - `/agentdev:audit-ste100` checks the rule. A finding stops the
        change until the text is corrected.
  ```

- [ ] `docs/knowledge/AGENTS.md#conventions` holds this bullet:

  ``` markdown
  - **Prose follows ASD-STE100 Issue 9.** Best Practice 15 in the repository
    `AGENTS.md` is the rule. `data/glossary.md` is the list of technical nouns
    and technical verbs that the rule permits.
  ```

- [ ] The `iwe-bootstrap` asset copy of `docs/knowledge/AGENTS.md` holds the
  same bullet.

- [ ] `docs/knowledge/data/product.md#authoring-rules` holds one bullet that
  states the rule and names Best Practice 15.

### Task 2: Bind the glossary page to a schema

**Files:** Modify: `.iwe/config.toml`, `docs/knowledge/SCHEMA.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/.iwe/config.toml`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/SCHEMA.md`

- [ ] `.iwe/config.toml#schemas.tracker` matches `data/glossary`.
- [ ] The `iwe-bootstrap` asset copy of `.iwe/config.toml` has the same match.
- [ ] `docs/knowledge/SCHEMA.md#hubs-and-the-trackers` names `data/glossary.md`
  as a `tracker` page.
- [ ] The `iwe-bootstrap` asset copy of `SCHEMA.md` names it too.

### Task 3: Write the glossary

**Files:** Create: `docs/knowledge/data/glossary.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/glossary.md`;
Modify: `docs/knowledge/data/index.md`,
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/index.md`

- [ ] `docs/knowledge/data/glossary.md` has `type: tracker`, `stage: living`,
  and a `description`.
- [ ] Each entry is one list item: the term in bold, then `(noun)` or `(verb)`,
  then the meaning in one sentence.
- [ ] The entries are in alphabetical order.
- [ ] Each term in `docs/spec-audit/specs.jsonl` under `glossary_terms` that
  prose uses as a word has an entry.
- [ ] No entry is a term that is only a code identifier, such as a file name or
  a result code.
- [ ] Each meaning agrees with the code or the rulebook that defines the term.
- [ ] `docs/knowledge/data/index.md#reference` links the glossary.
- [ ] The `iwe-bootstrap` seed holds a glossary page that has no entries.
- [ ] The seed copy of `data/index.md` links the glossary.

### Task 4: Add the `audit-ste100` skill

**Files:** Create: `.agents/plugins/agentdev/skills/audit-ste100/SKILL.md`;
Modify: `.agents/plugins/agentdev/README.md`, `README.md`

- [ ] The skill names the standard as ASD-STE100 Issue 9.
- [ ] The skill says that it checks from the model's knowledge of the standard
  and holds no copy of the standard or of its dictionary.
- [ ] The skill gives the same definition of prose as Best Practice 15: text in
  code formatting, text in a fenced block, and quoted text are not prose.
- [ ] The skill has three scopes. The file scope reads a whole file. The diff
  scope reads only the lines that a diff adds. The plan scope reads every
  section of a plan.
- [ ] The skill checks the writing rules of the standard, the words that the
  standard approves, and each project term against the glossary of the
  repository that it runs in.
- [ ] The report is one table. Each row gives the place as an anchor, the quoted
  text, the rule that the text breaks, and a replacement. A report with no row
  says that there are no findings.
- [ ] The skill edits no file in any scope.
- [ ] The skill table in `.agents/plugins/agentdev/README.md` lists the skill.
- [ ] The skill table in `README.md` lists the skill.

### Task 5: Add the `STE100 Auditor` agent

**Files:** Create: `.agents/plugins/agentdev/agents/ste100-auditor.agent.md`

- [ ] The agent has the tools `Bash`, `Read`, `Grep`, `Glob`, and `Skill`, and
  no tool that edits a file.
- [ ] The agent invokes `/agentdev:audit-ste100` with the file and the scope
  from its prompt, and returns the report unchanged.

### Task 6: Run the audit first in plan review

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md`,
`.agents/plugins/agentdev/agents/iwe-planner.agent.md`

- [ ] `/agentdev:iwe-plan-review` dispatches the `STE100 Auditor` alone, before
  any other agent. The prompt carries only the plan file path and the scope
  `plan`.
- [ ] When that report has a finding, the skill returns it under the agent's
  name and dispatches no other agent.
- [ ] When that report has no finding, the skill dispatches the
  `Durable Knowledge Auditor`, `iwe-plan-reviewer`, and `iwe-ship-reviewer` in
  one message and returns the four reports.
- [ ] Step 7 of `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps`
  tells Plan to correct each `STE100 Auditor` finding and to run the review
  again.

### Task 7: Run the audit in pull request review

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [ ] `.agents/plugins/agentdev/skills/pr-review/SKILL.md#review-focus` runs
  `/agentdev:audit-ste100` in the diff scope before `/agentdev:iwe-audit`.
- [ ] The pass reads the lines that the diff adds to docs and skills files, and
  the comments and docstrings that it adds to code files.
- [ ] A finding becomes an inline review comment under the same bar as a
  durable-knowledge finding, and it blocks.
- [ ] The pass does not read the pull request title, the pull request body, or a
  commit message.
- [ ] The table in
  `.agents/plugins/agentdev/skills/pr-review/SKILL.md#effort-tiers` has a row
  for the pass: `light` at light effort and `large` at full effort.

### Task 8: Observe the audit in a plan review

**Closed by:** the `/agentdev:iwe-plan-review` run on the next plan that a
session drafts after this change is on the default branch.

- [ ] The `STE100 Auditor` report returns before any other reviewer runs.
- [ ] After the draft has no finding, the review returns four reports.

## Spec changes

The repository owner decided that this plan writes spec text only for plan
review and for pull request review: one changed requirement and one added
requirement. The rule, the skill, and the glossary get no spec.

[agentdev IWE workflow skills](../spec/iwe-workflow-skills.md):

``` markdown
## MODIFIED Requirements

### Requirement: Plan review runs its reviewers from fresh contexts and changes nothing

`/agentdev:iwe-plan-review <plan>` SHALL first dispatch the `STE100 Auditor`
alone, with a prompt that carries only the plan file path and the scope `plan`.
When that report holds a finding, the skill SHALL return it verbatim under the
agent's name and SHALL dispatch no other agent. When it holds none, the skill
SHALL dispatch the `Durable Knowledge Auditor`, `iwe-plan-reviewer`, and
`iwe-ship-reviewer` in one message, forwarding no conversation turns: the
auditor's prompt SHALL carry only the plan file path and the scope `plan`,
`iwe-plan-reviewer`'s only the plan key and the absolute path of the skill's
`references/plan-rules.md`, and `iwe-ship-reviewer`'s only the plan key and the
mode `plan`. It SHALL perform no review step itself, SHALL return every report
verbatim under each agent's name, and SHALL edit no file and commit nothing;
applying the verdicts belongs to its caller. The skill SHALL be model-invocable,
so the `iwe-planner` rulebook can run it in every mode.

#### Scenario: Plan reaches its review step

- **WHEN** `iwe-planner` reaches its review step on a created or revised plan,
  and the `STE100 Auditor` reports no finding
- **THEN** the three other agents are dispatched in parallel with only those
  prompts, the four reports return unchanged, and the plan file is unchanged
  until Plan applies them

#### Scenario: The draft breaks the prose rule

- **WHEN** the `STE100 Auditor` reports a finding on the draft
- **THEN** only that report returns, no other agent is dispatched, and the plan
  file is unchanged
```

`## Rationale` entry that the spec gains: "The ASD-STE100 audit runs before the
other plan reviewers". It records the rejected fourth parallel reviewer.

[PR review](../spec/pr-review.md):

``` markdown
## ADDED Requirements

### Requirement: added prose gets an ASD-STE100 pass before the durable-knowledge pass

When the diff adds prose — a line in a docs or skills file, as "docs and skills
get a durable-knowledge pass" defines those files, or a comment or docstring in
a code file — `pr-review` SHALL run `/agentdev:audit-ste100` in diff scope over
those added lines before the durable-knowledge pass, at both effort tiers, and
SHALL NOT run it on a diff that adds none. Each finding SHALL become an inline
review comment on the diff line that holds its quoted text, kept only when the
added line can be quoted and the rule it breaks named, and SHALL be blocking.
The pass SHALL NOT read the pull request title, the pull request body, or a
commit message.

#### Scenario: a diff adds a code comment

- **WHEN** a pull request adds a comment to a code file and changes no docs or
  skills file
- **THEN** the ASD-STE100 pass reads the added comment, and no durable-knowledge
  pass runs.

#### Scenario: a diff adds no prose

- **WHEN** a pull request changes code lines and adds no comment, no docstring,
  and no line in a docs or skills file
- **THEN** no ASD-STE100 pass runs.
```

`## Rationale` entry that the spec gains: "The ASD-STE100 pass checks from the
model's knowledge of the standard". It records the rejected rule page, the
rejected dictionary check, the rejected counting script, and the rejected audit
of commit messages and pull request text.

## Verification

``` bash
uv run validate_agent_files --recommend . --require-marketplace claude
uv run pytest .agents/plugins/agentdev/tests/test_iwe_seed.py
uv run pytest docs/knowledge/tests
iwe normalize && iwe schema validate
uv run scripts/check-anchors.py
```

## Out of scope

- The conversion of text that existed before the rule. [Migrate existing prose
  to ASD-STE100](../backlog/migrate-prose-to-ste100.md) owns it.
- A check against the standard itself or its dictionary. [Full ASD-STE100
  compliance](../someday/ste100-full-compliance.md) owns it.
- An audit of commit messages, pull request titles, or pull request bodies.
- A change to `/agentdev:git-commit`, `/agentdev:pr-open`, or
  `/agentdev:pr-gen-description`.
- The removal of the `Durable Knowledge Auditor` agent or of
  `/agentdev:iwe-audit`.
- Decision records, and the removal of `data/spec/`.

## Key references

- `AGENTS.md#best-practices-for-agents` — the list that gains item 15.
- `docs/knowledge/AGENTS.md#conventions` — the list that gains the pointer.
- `docs/knowledge/data/product.md#authoring-rules` — the copy of the root rules
  that Plan reads.
- `.iwe/config.toml#schemas.tracker` — the binding that gains `data/glossary`.
- `docs/knowledge/SCHEMA.md#hubs-and-the-trackers` — where the `tracker` pages
  are named.
- `docs/knowledge/data/index.md#reference` — the section that links the
  glossary.
- `docs/spec-audit/specs.jsonl` — the seed terms, under `glossary_terms`.
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md#scope` — the scopes that
  the new skill follows.
- `.agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md` — the
  agent that the `STE100 Auditor` follows.
- `.agents/plugins/agentdev/skills/iwe-plan-review/SKILL.md#steps` — the
  dispatch that gains the first step.
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps` — step 7, which
  applies the reports.
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#review-focus` — the
  documentation focus that runs `/agentdev:iwe-audit`.
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#effort-tiers` — the slot
  table.
- `.agents/plugins/agentdev/tests/test_iwe_seed.py::test_scaffold_support_files_match_the_publisher_workspace`
  — the test that compares the asset copies with the workspace.
