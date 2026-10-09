---
type: architecture
description: Why the Ship and Implement rulebooks live in catalog agents that only explicit-only skills and named dispatchers start, why Ship always runs as a subagent with a conversation-free prompt, and the harness behavior on Claude Code, Codex, and OpenCode that the gate rests on.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-08T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
---

# Explicit-only workflow agents

## Decision

The Ship and Implement workflows are each defined once, as the catalog agents
`iwe-shipper` and `iwe-implementer` in `.agents/plugins/agentdev/agents/`. The
skills that start them carry no rules of their own.

- **Who may start them.** Only these callers:

  - the user's `/agentdev:iwe-ship` and `/agentdev:iwe-implement`;
  - the `/agentdev:iwe-ship-all` and `/agentdev:iwe-implement-all` coordinators,
    which the user starts;
  - `/agentdev:iwe-plan` revise mode, when the revision answers a Ship blocker
    report for that plan, which re-dispatches `iwe-shipper` after validation.

  Each agent's `description` names its dispatchers, so nothing else matches it.

- **The gate is explicit-only on all three harnesses.** The two entry skills,
  the two coordinators, and every other skill with
  `disable-model-invocation: true` also ship `agents/openai.yaml` with
  `policy.allow_implicit_invocation: false`. The first key gates Claude Code
  and, through the bridge's `deny`, OpenCode; the second gates Codex. A test
  keeps the two in step.

- **Ship always runs as a dispatched subagent**, including the user's own
  `/agentdev:iwe-ship`. Its verification must rest on the code and the graph,
  never on what a conversation asserted. The dispatch prompt carries only the
  plan key, the operation (ship, cancel, or release `<X.Y.Z>`), and any user
  approval quoted verbatim. An approval the Shipper needs comes back in its
  report, and the user re-runs `/agentdev:iwe-ship` granting it.

- **Implement keeps the user's session for a direct run.**
  `/agentdev:iwe-implement` has the session follow the `iwe-implementer`
  rulebook in place, so it can ask about an ambiguous plan or a material
  deviation. Only `iwe-implement-all` dispatches it.

- **A dispatched agent cannot reach the user.** Wherever its rulebook would ask,
  it stops without taking the step and reports the decision it needs.

## Host behavior the design rests on

These hold for Claude Code 2.1.280, Codex 0.156.1, and OpenCode 1.18.34. A
version bump is the point at which to recheck them.

### Fixture

A scratch git repository with two skills that differ only in their gate, and two
Claude agents that preload them:

``` text
<skills>/gated/SKILL.md          # disable-model-invocation: true
<skills>/open/SKILL.md           # no gate (Claude fixture)
<skills>/policy/SKILL.md         # disable-model-invocation: true (Codex fixture)
<skills>/policy/agents/openai.yaml
.claude/agents/preloader.md      # skills: [gated]
.claude/agents/preloader-open.md # skills: [open]
```

`<skills>` is `.claude/skills` for Claude Code and `.agents/skills` for Codex.
Each skill body is one line naming a unique marker:

``` markdown
---
name: gated
description: Print the gated marker. Use when asked for the gated marker.
disable-model-invocation: true
---

The marker is GATED-MARKER-4417.
```

`policy/agents/openai.yaml`:

``` yaml
policy:
  allow_implicit_invocation: false
```

`preloader.md` (and `preloader-open.md` with `open`):

``` markdown
---
name: preloader
description: Reports the marker from its preloaded skill.
skills:
  - gated
---

Report the marker your preloaded skill gives, or NONE if no skill content was preloaded. Do not use any tool.
```

### Claude Code

- **The gate covers subagents.** Asked to load `gated` with the Skill tool,
  directly or from a dispatched general-purpose subagent, the tool refuses:
  "Skill gated cannot be used with Skill tool due to disable-model-invocation. …
  Do not replicate this skill's workflow by other means". A coordinator that
  dispatches `/agentdev:iwe-ship` as a subagent prompt therefore cannot run.

  ``` bash
  claude -p 'Call the Skill tool with skill "gated" and report any error verbatim.' </dev/null
  ```

- **An agent's `skills:` preload withholds a gated skill.** Dispatched as
  subagents, `preloader` answers NONE and `preloader-open` answers
  OPEN-MARKER-9021. (`claude --agent` runs the agent as the main thread, which
  applies no preload, so it is not a valid control.)

  ``` bash
  claude -p 'Use the Agent tool with subagent_type "preloader" and prompt
    "What marker does your preloaded skill give? Use no tools." Relay its answer.' </dev/null
  ```

- **Reading the skill file is not gated.** A subagent told to Read
  `.claude/skills/gated/SKILL.md` gets the marker. Only the refusal text above
  forbids that route, so it rests on the model.

- **A hook sees the call, not its cause.** A `PreToolUse` hook on `Agent|Skill`
  receives `session_id`, `transcript_path`, `cwd`, `permission_mode`,
  `prompt_id`, `effort`, `tool_use_id`, `tool_name`, and `tool_input` (for
  Agent: `description`, `prompt`, `subagent_type`, `run_in_background`). Nothing
  names the skill or the request that led to the call.

### Codex

- **`disable-model-invocation` is ignored.** Asked to list its available skills,
  Codex lists `gated`, which carries only that key.

- **`policy.allow_implicit_invocation: false` removes the skill from that list**
  while `$policy` still runs it explicitly and returns POLICY-MARKER-5530.

  ``` bash
  codex exec 'List the name of every skill in your available-skills list, one per line.' </dev/null
  codex exec '$policy — reply with the marker the skill gives.' </dev/null
  ```

### OpenCode

The bridge's `permission.skill.<name> = "deny"` removes a gated skill from the
model's list and makes the skill tool refuse it, while its `agentdev:<name>`
command still runs; see [OpenCode catalog bridge](opencode-catalog-bridge.md).

## Rejected alternatives

- **Drop the gate and rely on descriptions.** An ungated skill is listed to the
  model with its description on every harness, so a description match can start
  Ship from Explore — for example after a partial answer closes a plan's open
  question.
- **Preload the gated skill into the agent.** Claude Code withholds a gated
  skill from an agent's `skills:` preload, so the agent starts without its
  rulebook.
- **Keep the rulebook in the gated skill and have the subagent read its file.**
  The read succeeds, but it is exactly the route the Skill tool's refusal tells
  the model not to take, so a model may rightly refuse it, and one that complies
  has bypassed the gate.
- **A self-checking skill or a harness hook.** A skill that checks who invoked
  it is a prompt-level check a model can argue past. A hook's input names the
  tool call, not the skill or request behind it, so it cannot tell a
  coordinator's dispatch from Explore's without parsing the transcript, and it
  needs one implementation per harness.
