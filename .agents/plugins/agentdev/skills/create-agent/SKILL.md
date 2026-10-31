---
name: create-agent
description: Create or update repository subagents shared by Claude Code and OpenCode. Use when adding an agent in the agentdev plugin catalog or defining its delegation scope, tools, and instructions.
---

# Create Custom Agent

Instructions for creating effective and maintainable custom agents (subagents) that provide specialized expertise for specific development tasks in Claude Code.

## Project Context

- Target audience: Developers creating custom agents for Claude Code
- File format: Markdown with YAML frontmatter
- File naming convention: lowercase with hyphens, `.agent.md` suffix (e.g., `test-specialist.agent.md`)
- Location: `.agents/plugins/agentdev/agents/` (the `agentdev` plugin catalog, canonical in this repository), a consuming project's own project-level agents directory, `~/.claude/agents/` (personal, user-wide)
- Purpose: Define specialized agents with tailored expertise, tools, and instructions for specific tasks
- Official documentation: https://code.claude.com/docs/en/sub-agents

Claude Code discovers every `*.md` file in the plugin's `agents/` directory, and
OpenCode's bridge plugin loads every `*.agent.md` there. Name agent files with the
`.agent.md` suffix so both harnesses load them and the validator recognizes them.

## Agent Frontmatter

Every agent file must include `name` and `description`. Add `tools` or `model`
only when their defaults do not suit the agent:

```yaml
---
name: test-specialist
description: Brief description of the agent purpose and when to delegate to it
tools: Bash, Read, Edit, Write, Grep, Glob
model: inherit
---
```

### Core Frontmatter Properties

#### **name** (REQUIRED)

- Unique identifier used when invoking the agent
- Use lowercase letters and hyphens; the filename need not match it
- Example: `test-specialist`

#### **description** (REQUIRED)

- Clearly states the agent's purpose, domain expertise, and **when Claude should delegate to it**
- Claude uses this description to decide when to hand a task to the agent automatically, so include trigger scenarios ("Use during the Red phase of TDD — before any implementation exists")
- Should be concise (50-250 characters) and actionable

#### **tools** (OPTIONAL)

- Comma-separated string (or YAML list) of Claude Code tool names the agent can use
- If omitted, the agent inherits all tools available to the main conversation
- Common tools: `Bash`, `Read`, `Edit`, `Write`, `Grep`, `Glob`, `WebSearch`, `WebFetch`, `Agent`, `TodoWrite`
- MCP tools use the `mcp__<server>__<tool>` naming scheme

#### **model** (OPTIONAL)

- Model the agent runs on. Use an available alias (`sonnet`, `opus`, `haiku`,
  or `fable`), `inherit` to use the parent conversation's model, or a full
  model ID supported by the active provider (for example, `claude-opus-4-8`)
- If omitted, the configured subagent default is used
- Choose based on agent complexity: `haiku` for mechanical tasks, `sonnet`/`opus` for judgment-heavy work

### Tool Selection Best Practices

- **Principle of Least Privilege**: Only enable tools necessary for the agent's purpose
- **Security**: Limit `Bash` access unless command execution is explicitly required
- **Focus**: Fewer tools = clearer agent purpose and better performance
- **Read-only agents**: Reviewers and analysts should get `Read`, `Grep`, `Glob` — not `Edit`/`Write`

## Agent Prompt Structure

The markdown content below the frontmatter defines the agent's behavior, expertise, and instructions. Well-structured prompts typically include:

1. **Agent Identity and Role**: Who the agent is and its primary role
2. **Core Responsibilities**: What specific tasks the agent performs
3. **Approach and Methodology**: How the agent works to accomplish tasks
4. **Guidelines and Constraints**: What to do/avoid and quality standards
5. **Output Expectations**: Expected output format and quality

### Prompt Writing Best Practices

- **Be Specific and Direct**: Use imperative mood ("Analyze", "Generate"); avoid vague terms
- **Define Boundaries**: Clearly state scope limits and constraints
- **Include Context**: Explain domain expertise and reference relevant frameworks
- **Focus on Behavior**: Describe how the agent should think and work
- **Use Structured Format**: Headers, bullets, and lists make prompts scannable
- **Remember the agent starts cold**: A subagent does not see the parent conversation; the prompt (plus what the orchestrator passes in) is all the context it gets

## Sub-Agent Orchestration

Agents can invoke other agents using the **Agent tool** to orchestrate multi-step workflows (e.g., the Principal Engineer agent orchestrating the TDD Red → Green → Refactor cycle).

### How It Works

1. Include `Agent` in the orchestrator's `tools` list
2. For each step, invoke a sub-agent with `subagent_type` set to the target agent's name and a `prompt` carrying the essential context
3. The sub-agent's final message is returned to the orchestrator — ask for a clear summary of actions taken, files modified, and issues found

### Orchestration Guidelines

- **Pass minimal, explicit context**: Paths, identifiers, and expected outputs — not entire file contents
- **Sequential execution**: Run steps in order when outputs feed later steps; independent steps can run in parallel
- **Return summaries**: Each sub-agent should report what it accomplished
- **Error handling**: Check results before proceeding to dependent steps
- **Don't over-orchestrate**: Each sub-agent invocation adds latency and re-derives context. Avoid pipelines of more than a handful of steps or bulk data processing through sub-agents; implement high-volume logic directly instead

### Example Step Invocation

```text
Step 1: Write failing tests
Agent: TDD Red
Prompt: Work on issue #123 in py_packages/example_package.
        Write failing tests for the retry-with-backoff behaviour described in the issue.
        Return: test files created, how each test fails, open questions.
```

## Agent Creation Checklist

### Frontmatter

- [ ] `name` present and descriptive
- [ ] `description` states what the agent does **and when to delegate to it**
- [ ] `tools` limited to what the agent needs (or intentionally omitted to inherit all)
- [ ] `model` set when the default is not appropriate

### Prompt Content

- [ ] Clear agent identity and role defined
- [ ] Core responsibilities listed explicitly
- [ ] Approach and methodology explained
- [ ] Guidelines and constraints specified
- [ ] Output expectations documented
- [ ] Instructions are specific and actionable
- [ ] Scope and boundaries clearly defined

### File Structure

- [ ] Filename follows lowercase-with-hyphens convention with `.agent.md` suffix
- [ ] File placed in `.agents/plugins/agentdev/agents/`
- [ ] Relative links to skills (for example,
      `../skills/create-skill/SKILL.md`) and sibling agents resolve

### Quality Assurance

- [ ] Agent purpose is unique and not duplicative
- [ ] Tools are minimal and necessary
- [ ] Agent has been tested with representative tasks
- [ ] `validate_agent_files` passes (run by pre-commit and CI)

## Common Mistakes to Avoid

- ❌ Missing `description`, or a description that says _what_ but not _when_ — the agent will never be selected automatically
- ❌ Granting all tools to a read-only reviewer agent
- ❌ Referencing tools that don't exist in Claude Code (tool aliases from other assistants)
- ❌ Assuming the sub-agent can see the parent conversation — it can't; pass context explicitly
- ❌ Creating a separate per-harness copy instead of editing the canonical
  `.agents/plugins/agentdev/agents/` spec
- ❌ Vague, ambiguous instructions or conflicting guidelines
- ❌ Using spaces or special characters in filenames

## Testing and Validation

1. Create the agent file with proper frontmatter
2. Run `uv run validate_agent_files .agents/plugins/agentdev/agents --kind agents --ci` (also
   enforced by pre-commit and CI)
3. Test with representative tasks: explicit invocation ("Use the TDD Red
   agent to…") and automatic delegation
4. Verify tool access works as expected and the agent stays within scope.
   Claude Code detects changes in an existing agents directory
   automatically; restart only if that directory did not exist when the
   session began.

## Additional Resources

- [Claude Code subagents documentation](https://code.claude.com/docs/en/sub-agents)
- [create-skill](../create-skill/SKILL.md) — for creating skills
- Existing agents in `.agents/plugins/agentdev/agents/` — use as reference implementations
