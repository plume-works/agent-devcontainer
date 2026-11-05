---
type: architecture
description: Why the Ship and Implement rulebooks live in catalog agents, why the coordinators start only from explicit-only skills while any session asked to ship or implement a named plan may load Ship or Implement, why Ship always runs as a subagent with a conversation-free prompt, and the harness behavior on Claude Code and OpenCode that the gate rests on.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-05T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
---

# Explicit-only workflow agents

## Decision

The Ship and Implement workflows are each defined once, as the catalog agents
`iwe-shipper` and `iwe-implementer` in `.agents/plugins/agentdev/agents/`. The
skills that start them carry no rules of their own.

- **Who may start them.** Only these callers:

  - for Ship, any session asked to ship a named plan — by the user's
    `/agentdev:iwe-ship`, by a plain request, or by a message from a coordinator
    session — which loads `/agentdev:iwe-ship`;
  - for Implement, any session asked to implement a named plan — by the user's
    `/agentdev:iwe-implement`, by a plain request, or by a message from a
    coordinator session — which loads `/agentdev:iwe-implement`;
  - the `/agentdev:iwe-ship-all` and `/agentdev:iwe-implement-all` coordinators,
    which the user starts;
  - `/agentdev:iwe-plan` revise mode, when the revision answers a Ship blocker
    report for that plan, which re-dispatches `iwe-shipper` after validation.

  Each agent's `description` names its dispatchers, so nothing else matches it.

- **The gate is explicit-only on both harnesses.** Of the entry points, only the
  coordinators `iwe-ship-all` and `iwe-implement-all` carry the
  `disable-model-invocation: true` frontmatter key, as does every other gated
  skill. It gates Claude Code directly and OpenCode through the bridge's `deny`.

- **Implement's entry skill is model-invocable.** `iwe-implement` carries no
  gate, and its description matches only a request that names a plan. It needs a
  named active plan whose dependencies are done and asks when the plan is
  ambiguous, so a stray match has nothing to build; and Plan and Explore, the
  sessions where a stray start could happen, never name it as a next step.

- **Ship's entry skill is model-invocable.** The gate's job is to keep
  conversation context out of Ship, and Ship always runs as a fresh
  `iwe-shipper` subagent whose prompt carries only the plan key, the operation,
  and quoted approvals, so the gate adds nothing to that. `iwe-ship` matches
  only a request that names a plan to ship or cancel, or a release to cut, and
  Explore's rules forbid it from loading the skill or dispatching the Shipper.

- **Ship always runs as a dispatched subagent**, including the user's own
  `/agentdev:iwe-ship`. Its verification must rest on the code and the graph,
  never on what a conversation asserted. The dispatch prompt carries only the
  plan key, the operation (ship, cancel, or release `<X.Y.Z>`), and any user
  approval quoted verbatim. An approval the Shipper needs comes back in its
  report, and the user re-runs `/agentdev:iwe-ship` granting it. A coordinator
  session may relay the user's approvals to a session it asks to ship a plan;
  that session quotes a relayed approval the same way as one the user typed.

- **Implement keeps the user's session for a direct run.**
  `/agentdev:iwe-implement` has the session that loaded it follow the
  `iwe-implementer` rulebook in place, so it can ask about an ambiguous plan or
  a material deviation. A decision the rulebook asks for comes from that
  session's own user, or from an approval of the user's that a coordinator
  session relays in its message; the coordinator asks the user in one place and
  passes the answers on. Only `iwe-implement-all` dispatches the agent.

- **A dispatched agent cannot reach the user.** Wherever its rulebook would ask,
  it stops without taking the step and reports the decision it needs.

## Host behavior the design rests on

These hold for Claude Code 2.1.280 and OpenCode 1.18.34. A version bump is the
point at which to recheck them.

### Fixture

A scratch git repository with two skills that differ only in their gate, and two
Claude agents that preload them:

``` text
<skills>/gated/SKILL.md          # disable-model-invocation: true
<skills>/open/SKILL.md           # no gate (Claude fixture)
.claude/agents/preloader.md      # skills: [gated]
.claude/agents/preloader-open.md # skills: [open]
```

`<skills>` is `.claude/skills` for Claude Code. Each skill body is one line
naming a unique marker:

``` markdown
---
name: gated
description: Print the gated marker. Use when asked for the gated marker.
disable-model-invocation: true
---

The marker is GATED-MARKER-4417.
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

### OpenCode

The bridge's `permission.skill.<name> = "deny"` removes a gated skill from the
model's list and makes the skill tool refuse it, while its `agentdev:<name>`
command still runs; see [OpenCode catalog bridge](opencode-catalog-bridge.md).

The user's config loads the bridge by absolute path, so the catalog sits outside
any project. Reading `agents/iwe-implementer.agent.md` from
`/agentdev:iwe-implement` therefore needs OpenCode's `external_directory`
permission: interactive OpenCode asks, and `opencode run` auto-rejects it. A
headless run grants it in the project's `opencode.json`:

``` json
{"permission": {"external_directory": {"<catalog root>/agents/*": "allow"}}}
```

## Rejected alternatives

- **Drop the gate and rely on descriptions, for the coordinators.** An ungated
  skill is listed to the model with its description on every harness, so a
  description match could start a run over every plan from any session, Explore
  included — for example after a partial answer closes a plan's open question.
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
- **A separate model-invocable Implement entry skill that runs only on a
  coordinator's request.** Its description is still listed to the model, and the
  "only on a coordinator's request" check is a prompt-level self-check, the same
  weakness as a self-checking skill.
- **Workers following the rulebook file without the skill.** A worker that tried
  the gated skill first sees the refusal text, which tells it not to replicate
  the workflow by other means, so the route depends on the coordinator never
  mentioning the skill.
