import { describe, expect, test } from "bun:test"
import { readdirSync, readFileSync } from "node:fs"
import path from "node:path"
import plugin, {
  TOOL_PERMISSIONS,
  SUBAGENT_TOOL_PERMISSIONS,
  bridge,
} from "../../.opencode-plugin/index.ts"

const root = path.resolve(import.meta.dir, "../..")
const skillsDir = path.join(root, "skills")
const agentsDir = path.join(root, "agents")
const namespace = JSON.parse(readFileSync(path.join(root, ".claude-plugin/plugin.json"), "utf8")).name

function frontmatter(file: string): Record<string, unknown> {
  const text = readFileSync(file, "utf8")
  return Bun.YAML.parse(text.split(/^---$/m)[1]) as Record<string, unknown>
}

const skills = readdirSync(skillsDir)
  .map((dir) => path.join(skillsDir, dir, "SKILL.md"))
  .filter((file) => Bun.file(file).size > 0)
  .map((file) => ({ dir: path.dirname(file), meta: frontmatter(file) }))

const agents = readdirSync(agentsDir)
  .filter((file) => file.endsWith(".agent.md"))
  .map((file) => ({
    stem: file.slice(0, -".agent.md".length),
    meta: frontmatter(path.join(agentsDir, file)),
  }))

function claudeTools(meta: Record<string, unknown>): string[] {
  return String(meta.tools)
    .split(",")
    .map((tool) => tool.trim())
}

async function configured(config: Record<string, any> = {}) {
  const hooks = await bridge(root)
  await hooks.config!(config as any)
  return config
}

describe("config hook", () => {
  test("adds the catalog skills directory to skills.paths", async () => {
    const config = await configured({ skills: { paths: ["/elsewhere"] } })
    expect(config.skills.paths).toEqual(["/elsewhere", skillsDir])
  })

  test("registers every skill as a namespaced command ending with the base-directory footer", async () => {
    const config = await configured()
    expect(skills.length).toBeGreaterThan(0)
    for (const { dir, meta } of skills) {
      const command = config.command[`${namespace}:${meta.name}`]
      expect(command.description).toBe(meta.description)
      expect(command.template).toEndWith(
        `\n\nBase directory for this skill: ${dir}\n` +
          "Relative paths in this skill (e.g., scripts/, references/) are relative to this base directory.",
      )
    }
  })

  test("denies every disable-model-invocation skill to the skill tool, and no other", async () => {
    const config = await configured()
    const explicitOnly = skills.filter(({ meta }) => meta["disable-model-invocation"] === true)
    expect(explicitOnly.length).toBeGreaterThan(0)
    const expected = Object.fromEntries(explicitOnly.map(({ meta }) => [meta.name, "deny"]))
    expect(config.permission.skill).toEqual(expected)
  })

  test("maps every Claude tool a catalog agent uses", () => {
    for (const { meta } of agents) {
      for (const tool of claudeTools(meta)) expect(TOOL_PERMISSIONS).toHaveProperty(tool)
    }
  })

  test("registers every agent as a subagent denied exactly the tools it omits", async () => {
    const config = await configured()
    expect(agents.length).toBeGreaterThan(0)
    for (const { stem, meta } of agents) {
      const agent = config.agent[stem]
      expect(agent.mode).toBe("subagent")
      expect(agent.description).toBe(meta.description)
      expect(agent.prompt.length).toBeGreaterThan(0)
      const allowed = new Set(claudeTools(meta).map((tool) => TOOL_PERMISSIONS[tool]))
      const omitted = SUBAGENT_TOOL_PERMISSIONS.filter((permission) => !allowed.has(permission))
      expect(agent.permission).toEqual(Object.fromEntries(omitted.map((p) => [p, "deny"])))
    }
  })

  test("tdd-red loses web and task tools and keeps bash unset", async () => {
    const config = await configured()
    const permission = config.agent["tdd-red"].permission
    expect(permission).toMatchObject({ webfetch: "deny", websearch: "deny", task: "deny" })
    expect(permission).not.toHaveProperty("bash")
  })

  test("leaves keys the user already defined alone", async () => {
    const userCommand = { template: "mine" }
    const userAgent = { prompt: "mine" }
    const config = await configured({
      command: { [`${namespace}:pr-open`]: userCommand },
      agent: { "tdd-red": userAgent },
      permission: { skill: { "iwe-plan": "allow" } },
    })
    expect(config.command[`${namespace}:pr-open`]).toBe(userCommand)
    expect(config.agent["tdd-red"]).toBe(userAgent)
    expect(config.permission.skill["iwe-plan"]).toBe("allow")
    expect(config.permission.skill["iwe-ship"]).toBe("deny")
  })

  test("keeps a user's blanket skill permission ahead of the bridge's denies", async () => {
    const config = await configured({ permission: { skill: "ask" } })
    expect(Object.entries(config.permission.skill)[0]).toEqual(["*", "ask"])
    expect(config.permission.skill["iwe-ship"]).toBe("deny")
  })
})

describe("tool.execute.before hook", () => {
  async function rewrite(tool: string, args: Record<string, unknown>) {
    const hooks = await bridge(root)
    const output = { args: { ...args } }
    await hooks["tool.execute.before"]!({ tool, sessionID: "s", callID: "c" }, output)
    return output.args
  }

  test("strips the namespace from the skill tool's name", async () => {
    expect(await rewrite("skill", { name: `${namespace}:iwe-plan` })).toEqual({ name: "iwe-plan" })
  })

  test("leaves a bare skill name untouched", async () => {
    expect(await rewrite("skill", { name: "iwe-plan" })).toEqual({ name: "iwe-plan" })
  })

  test("leaves other tools' calls untouched", async () => {
    const args = { name: `${namespace}:iwe-plan`, command: `${namespace}:iwe-plan` }
    expect(await rewrite("bash", args)).toEqual(args)
  })
})

test("default export is a v1 plugin module", () => {
  expect(typeof plugin.id).toBe("string")
  expect(typeof plugin.server).toBe("function")
})
