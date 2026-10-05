// OpenCode bridge for the agentdev catalog. It must stay free of runtime
// dependencies: see architecture/opencode-catalog-bridge.
import type { Hooks, PluginInput, PluginModule } from "@opencode-ai/plugin"
import { existsSync, readdirSync, readFileSync } from "node:fs"
import path from "node:path"

/** OpenCode permission each Claude tool name maps to. */
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

/** OpenCode built-in tool permissions a catalog subagent is denied unless it maps to them. */
export const SUBAGENT_TOOL_PERMISSIONS: readonly string[] = [
  ...new Set(Object.values(TOOL_PERMISSIONS)),
  "lsp",
  "question",
]

type Action = "ask" | "allow" | "deny"
type Frontmatter = Record<string, unknown>
type Rule = Action | Record<string, Action>

// The SDK's Config type predates skills.paths and permission.skill, which the
// 1.18 runtime accepts; this names only the keys the bridge touches.
interface BridgeConfig {
  skills?: { paths?: string[] }
  command?: Record<string, unknown>
  agent?: Record<string, unknown>
  permission?: Action | Record<string, Rule>
}

interface Catalog {
  namespace: string
  skillsDir: string
  commands: Record<string, { description: string; template: string }>
  explicitOnly: string[]
  agents: Record<string, { description: string; mode: "subagent"; prompt: string; permission: Record<string, Action> }>
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
  const catalog: Catalog = { namespace: manifest.name, skillsDir, commands: {}, explicitOnly: [], agents: {} }

  for (const entry of readdirSync(skillsDir, { withFileTypes: true })) {
    const file = path.join(skillsDir, entry.name, "SKILL.md")
    if (!entry.isDirectory() || !existsSync(file)) continue
    const { meta, body } = readMarkdown(file)
    const name = String(meta.name)
    // Same footer OpenCode appends to its own skill-derived commands.
    catalog.commands[`${catalog.namespace}:${name}`] = {
      description: String(meta.description ?? ""),
      template: [
        body,
        "",
        `Base directory for this skill: ${path.dirname(file)}`,
        "Relative paths in this skill (e.g., scripts/, references/) are relative to this base directory.",
      ].join("\n"),
    }
    if (meta["disable-model-invocation"] === true) catalog.explicitOnly.push(name)
  }

  for (const file of existsSync(agentsDir) ? readdirSync(agentsDir) : []) {
    if (!file.endsWith(".agent.md")) continue
    const { meta, body } = readMarkdown(path.join(agentsDir, file))
    const granted = new Set(
      String(meta.tools ?? "")
        .split(",")
        .map((tool) => TOOL_PERMISSIONS[tool.trim()])
        .filter(Boolean),
    )
    const permission = Object.fromEntries(
      SUBAGENT_TOOL_PERMISSIONS.filter((p) => !granted.has(p)).map((p) => [p, "deny" as const]),
    )
    catalog.agents[file.slice(0, -".agent.md".length)] = {
      description: String(meta.description ?? ""),
      mode: "subagent",
      prompt: body,
      permission,
    }
  }
  return catalog
}

function applyCatalog(config: BridgeConfig, catalog: Catalog): void {
  const skills = (config.skills ??= {})
  skills.paths = [...(skills.paths ?? []), catalog.skillsDir]

  const commands = (config.command ??= {})
  for (const [name, command] of Object.entries(catalog.commands)) commands[name] ??= command

  const agents = (config.agent ??= {})
  for (const [name, agent] of Object.entries(catalog.agents)) agents[name] ??= agent

  if (catalog.explicitOnly.length === 0) return
  const rawPermission = config.permission ?? {}
  const permission = typeof rawPermission === "string" ? { "*": rawPermission } : rawPermission
  const rawSkill = permission.skill ?? {}
  const skill = typeof rawSkill === "string" ? { "*": rawSkill } : rawSkill
  for (const name of catalog.explicitOnly) skill[name] ??= "deny"
  permission.skill = skill
  config.permission = permission
}

/** Build the bridge's hooks for the catalog plugin rooted at `root`. */
export async function bridge(root: string): Promise<Hooks> {
  const catalog = readCatalog(root)
  const prefix = `${catalog.namespace}:`
  return {
    config: async (config) => applyCatalog(config as BridgeConfig, catalog),
    // Catalog text names sibling skills as /agentdev:<name>; the skill tool knows them bare.
    "tool.execute.before": async (input, output) => {
      const name = output.args?.name
      if (input.tool === "skill" && typeof name === "string" && name.startsWith(prefix)) {
        output.args.name = name.slice(prefix.length)
      }
    },
  }
}

export default {
  id: "agentdev-opencode-bridge",
  server: (_input: PluginInput) => bridge(path.resolve(import.meta.dir, "..")),
} satisfies PluginModule
