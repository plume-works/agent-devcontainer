// OpenCode bridge for the agentdev catalog. It must stay free of runtime
// dependencies: see architecture/opencode-catalog-bridge.
import type { Hooks, PluginInput, PluginModule } from "@opencode-ai/plugin"
import { existsSync, readdirSync, readFileSync } from "node:fs"
import path from "node:path"
import { registerWorkspace } from "./workspace-index.ts"
import type { RegistrationAdapters, WorkspaceConfig } from "./workspace-index.ts"

/** OpenCode v1 permission each Claude tool name maps to. */
export const TOOL_PERMISSIONS: Readonly<Record<string, string>> = {
  Bash: "bash",
  Read: "read",
  Edit: "edit",
  Write: "edit",
  Grep: "grep",
  Glob: "glob",
  WebSearch: "websearch",
  WebFetch: "webfetch",
  Agent: "task",
  TodoWrite: "todowrite",
  Skill: "skill",
}

/** OpenCode v1 built-in tool permissions a catalog subagent is denied unless it maps to them. */
export const SUBAGENT_TOOL_PERMISSIONS: readonly string[] = [
  ...new Set(Object.values(TOOL_PERMISSIONS)),
  "lsp",
  "question",
]

/** OpenCode v2 permission actions each Claude tool name maps to. */
export const V2_TOOL_ACTIONS: Readonly<Record<string, readonly string[]>> = {
  Bash: ["shell"],
  Read: ["read"],
  Edit: ["edit", "write", "patch"],
  Write: ["edit", "write", "patch"],
  Grep: ["grep"],
  Glob: ["glob"],
  WebSearch: ["websearch"],
  WebFetch: ["webfetch"],
  Agent: ["subagent"],
  TodoWrite: [],
  Skill: ["skill"],
}

/** OpenCode v2 actions a catalog subagent is denied unless it maps to them. */
export const V2_SUBAGENT_ACTIONS: readonly string[] = [
  ...new Set(Object.values(V2_TOOL_ACTIONS).flat()),
  "question",
]

type Action = "ask" | "allow" | "deny"
type Frontmatter = Record<string, unknown>
type Rule = Action | Record<string, Action>

// The SDK's Config type predates skills.paths and permission.skill, which the
// 1.18 runtime accepts; this names only the keys the bridge touches.
interface BridgeConfig extends WorkspaceConfig {
  skills?: { paths?: string[] }
  command?: Record<string, unknown>
  agent?: Record<string, unknown>
  permission?: Action | Record<string, Rule>
}

interface CatalogSkill {
  name: string
  description: string
  file: string
  body: string
  explicitOnly: boolean
}

interface CatalogAgent {
  stem: string
  description: string
  body: string
  tools: string[]
}

interface Catalog {
  namespace: string
  skillsDir: string
  skills: CatalogSkill[]
  agents: CatalogAgent[]
}

// The v2 plugin ctx, narrowed to what the bridge uses; registrations resolve
// to a disposable the bridge never needs.
type Registration = Promise<unknown>
interface V2Context {
  location: { directory: string }
  mcp: { transform: (fn: (editor: { get: (name: string) => unknown }) => void) => Registration }
  skill: { transform: (fn: (editor: { add: (skill: Record<string, unknown>) => void }) => void) => Registration }
  command: {
    transform: (fn: (editor: { add: (command: V2Command) => void }) => void) => Registration
  }
  agent: {
    transform: (fn: (editor: { update: (id: string, fn: (agent: Record<string, any>) => void) => void }) => void) => Registration
    get: (input: { agentID: string }) => Promise<{ data?: { system?: string } }>
  }
  tool: { hook: (name: "execute.before", fn: (event: { tool: string; input: unknown }) => void) => Registration }
  session: {
    hook: (name: "context", fn: (context: { agent: string; tools: Record<string, unknown> }) => Promise<void>) => Registration
    prompt: (input: Record<string, unknown>) => Promise<unknown>
  }
  permission: {
    hook: (name: "evaluate", fn: (evaluation: { agent?: string; action: string; effect: string }) => Promise<void>) => Registration
  }
}

interface V2Command {
  name: string
  description?: string
  execute: (invocation: {
    sessionID: string
    prompt: {
      text: string
      files?: V2PromptReference[]
      agents?: V2PromptReference[]
      skills?: V2PromptReference[]
    }
    delivery: unknown
  }) => Promise<void>
}

interface V2PromptReference {
  id?: string
  mention?: { start: number; end: number; text: string }
  [key: string]: unknown
}

function rebaseMentions(references: V2PromptReference[] | undefined, offset: number): V2PromptReference[] | undefined {
  return references?.map(reference => reference.mention === undefined
    ? reference
    : {
        ...reference,
        mention: {
          ...reference.mention,
          start: reference.mention.start + offset,
          end: reference.mention.end + offset,
        },
      })
}

function readMarkdown(file: string): { meta: Frontmatter; body: string } {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/.exec(readFileSync(file, "utf8"))
  if (!match) throw new Error(`${file}: missing YAML frontmatter`)
  return { meta: (Bun.YAML.parse(match[1]) ?? {}) as Frontmatter, body: match[2].trim() }
}

function readCatalog(root: string): Catalog {
  const manifest = JSON.parse(readFileSync(path.join(root, ".claude-plugin/plugin.json"), "utf8"))
  const skillsDir = path.join(root, "skills")
  const agentsDir = path.join(root, "agents")
  const catalog: Catalog = { namespace: manifest.name, skillsDir, skills: [], agents: [] }

  for (const entry of readdirSync(skillsDir, { withFileTypes: true })) {
    const file = path.join(skillsDir, entry.name, "SKILL.md")
    if (!entry.isDirectory() || !existsSync(file)) continue
    const { meta, body } = readMarkdown(file)
    catalog.skills.push({
      name: String(meta.name),
      description: String(meta.description ?? ""),
      file,
      body,
      explicitOnly: meta["disable-model-invocation"] === true,
    })
  }

  for (const file of existsSync(agentsDir) ? readdirSync(agentsDir) : []) {
    if (!file.endsWith(".agent.md")) continue
    const { meta, body } = readMarkdown(path.join(agentsDir, file))
    catalog.agents.push({
      stem: file.slice(0, -".agent.md".length),
      description: String(meta.description ?? ""),
      body,
      tools: String(meta.tools ?? "").split(",").map((tool) => tool.trim()).filter(Boolean),
    })
  }
  return catalog
}

function applyCatalog(config: BridgeConfig, catalog: Catalog): void {
  const skills = (config.skills ??= {})
  skills.paths = [...(skills.paths ?? []), catalog.skillsDir]

  const commands = (config.command ??= {})
  for (const skill of catalog.skills) {
    // Same footer OpenCode appends to its own skill-derived commands.
    commands[`${catalog.namespace}:${skill.name}`] ??= {
      description: skill.description,
      template: [
        skill.body,
        "",
        `Base directory for this skill: ${path.dirname(skill.file)}`,
        "Relative paths in this skill (e.g., scripts/, references/) are relative to this base directory.",
      ].join("\n"),
    }
  }

  const agents = (config.agent ??= {})
  for (const agent of catalog.agents) {
    const granted = new Set(agent.tools.map((tool) => TOOL_PERMISSIONS[tool]).filter(Boolean))
    agents[agent.stem] ??= {
      description: agent.description,
      mode: "subagent",
      prompt: agent.body,
      permission: Object.fromEntries(
        SUBAGENT_TOOL_PERMISSIONS.filter((p) => !granted.has(p)).map((p) => [p, "deny" as const]),
      ),
    }
  }

  const explicitOnly = catalog.skills.filter((skill) => skill.explicitOnly)
  if (explicitOnly.length === 0) return
  const rawPermission = config.permission ?? {}
  const permission = typeof rawPermission === "string" ? { "*": rawPermission } : rawPermission
  const rawSkill = permission.skill ?? {}
  const skill = typeof rawSkill === "string" ? { "*": rawSkill } : rawSkill
  for (const { name } of explicitOnly) skill[name] ??= "deny"
  permission.skill = skill
  config.permission = permission
}

/** Build the bridge's v1 hooks for the catalog plugin rooted at `root`. */
export async function bridge(
  root: string,
  input?: Pick<PluginInput, "directory" | "client">,
  adapters: Partial<RegistrationAdapters> = {},
): Promise<Hooks> {
  const catalog = readCatalog(root)
  const prefix = `${catalog.namespace}:`
  return {
    config: async (config) => {
      applyCatalog(config as BridgeConfig, catalog)
      if (input) void registerWorkspace(input.directory, config as BridgeConfig, {
        log: message => input.client.app.log({ body: { service: "agentdev", level: "warn", message } }),
        ...adapters,
      })
    },
    // Catalog text names sibling skills as /agentdev:<name>; the skill tool knows them bare.
    "tool.execute.before": async (input, output) => {
      const name = output.args?.name
      if (input.tool === "skill" && typeof name === "string" && name.startsWith(prefix)) {
        output.args.name = name.slice(prefix.length)
      }
    },
  }
}

/**
 * Register the catalog plugin rooted at `root` through OpenCode v2's plugin ctx.
 * Nothing is awaited: v2 holds every request until setup's registrations settle.
 */
export function setupBridge(root: string, ctx: V2Context, adapters: Partial<RegistrationAdapters> = {}): void {
  const catalog = readCatalog(root)
  const prefix = `${catalog.namespace}:`

  void ctx.mcp.transform((editor) => {
    const entry = editor.get("codebase-memory-mcp")
    void registerWorkspace(ctx.location.directory, { mcp: { "codebase-memory-mcp": entry } }, adapters)
  })

  void ctx.skill.transform((editor) => {
    for (const skill of catalog.skills) {
      editor.add({
        id: skill.name,
        name: skill.name,
        description: skill.description,
        ...(skill.explicitOnly ? { autoinvoke: false } : {}),
        path: skill.file,
        content: skill.body,
      })
    }
  })

  void ctx.command.transform((editor) => {
    for (const skill of catalog.skills) {
      const command = `${prefix}${skill.name}`
      editor.add({
        name: command,
        description: skill.description,
        execute: async ({ sessionID, prompt, delivery }) => {
          const invocation = `/${command}${prompt.text === "" ? "" : ` ${prompt.text}`}`
          const offset = invocation.length - prompt.text.length
          await ctx.session.prompt({
            sessionID,
            text: invocation,
            files: rebaseMentions(prompt.files, offset),
            agents: rebaseMentions(prompt.agents, offset),
            skills: [...(rebaseMentions(prompt.skills, offset) ?? []), { id: skill.name }],
            delivery,
          })
        },
      })
    }
  })

  // Tool limits are enforced by the hooks below: the host appends the global
  // permission rules after any rule set here. See architecture/opencode-catalog-bridge.
  void ctx.agent.transform((editor) => {
    for (const agent of catalog.agents) {
      editor.update(agent.stem, (info) => {
        info.mode = "subagent"
        info.description = agent.description
        info.system = agent.body
      })
    }
  })

  const denied = new Map(catalog.agents.map((agent) => {
    const granted = new Set(agent.tools.flatMap((tool) => V2_TOOL_ACTIONS[tool] ?? []))
    return [agent.stem, { body: agent.body, actions: V2_SUBAGENT_ACTIONS.filter((a) => !granted.has(a)) }]
  }))
  // A user agent under a catalog id replaces the catalog agent, limits included.
  const limits = async (agentID: string | undefined): Promise<readonly string[]> => {
    const entry = agentID === undefined ? undefined : denied.get(agentID)
    if (!entry) return []
    const { data } = await ctx.agent.get({ agentID: agentID! })
    return data?.system === entry.body ? entry.actions : []
  }

  void ctx.session.hook("context", async (context) => {
    for (const action of await limits(context.agent)) delete context.tools[action]
  })
  void ctx.permission.hook("evaluate", async (evaluation) => {
    if ((await limits(evaluation.agent)).includes(evaluation.action)) evaluation.effect = "deny"
  })

  // Catalog text names sibling skills as /agentdev:<name>; the skill tool knows them bare.
  void ctx.tool.hook("execute.before", (event) => {
    const input = event.input as { id?: unknown } | undefined
    if (event.tool === "skill" && typeof input?.id === "string" && input.id.startsWith(prefix)) {
      event.input = { ...input, id: input.id.slice(prefix.length) }
    }
  })
}

const id = "agentdev-opencode-bridge"

/**
 * The v2 entry: run setupBridge through the host's own `fromPromise` adapter,
 * logging through the host's Effect context so warnings reach opencode.log.
 * `load` resolves the host's modules; v1 never calls this.
 */
export function v2Effect(
  root: string,
  ctx: unknown,
  load: (name: string) => any,
  adapters: Partial<RegistrationAdapters> = {},
): unknown {
  const { Effect } = load("effect")
  const { fromPromise } = load("@opencode/plugin/promise/adapter")
  return Effect.contextWith((context: unknown) => {
    const log = (message: string) => Effect.runPromiseWith(context)(
      Effect.logWarning(message).pipe(Effect.annotateLogs({ service: "agentdev" })),
    )
    return fromPromise({ id, setup: (v2: V2Context) => setupBridge(root, v2, { log, ...adapters }) }).effect(ctx)
  })
}

const root = path.resolve(import.meta.dir, "..")

export default {
  id,
  server: (input: PluginInput) => bridge(root, input),
  effect: (ctx: unknown) => v2Effect(root, ctx, require),
} satisfies PluginModule & { effect: (ctx: unknown) => unknown }
