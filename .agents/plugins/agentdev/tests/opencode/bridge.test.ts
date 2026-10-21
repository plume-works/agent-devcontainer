import { describe, expect, test } from "bun:test"
import { readdirSync, readFileSync } from "node:fs"
import path from "node:path"
import plugin, {
  TOOL_PERMISSIONS,
  SUBAGENT_TOOL_PERMISSIONS,
  V2_TOOL_ACTIONS,
  V2_SUBAGENT_ACTIONS,
  bridge,
  setupBridge,
  v2Effect,
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

test("default export loads in OpenCode v1 and v2 without v2's modules", () => {
  expect(typeof plugin.id).toBe("string")
  expect(typeof plugin.server).toBe("function")
  expect(typeof plugin.effect).toBe("function")
  expect(plugin).not.toHaveProperty("setup")
  // The module imported above although neither v2 module resolves from it.
  for (const name of ["effect", "@opencode/plugin/promise/adapter"]) {
    expect(() => Bun.resolveSync(name, path.join(root, ".opencode-plugin"))).toThrow()
  }
})

test("pending workspace registration does not delay catalog or skill hooks", async () => {
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  let indexingPending = false
  const hooks = await bridge(root, { directory: root } as any, {
    run: async command => {
      if (command[0] === "git") return { exitCode: 0, stdout: root, stderr: "" }
      indexingPending = true
      await pending
      return { exitCode: 0, stdout: JSON.stringify({ structuredContent: { projects: [{ root_path: root }], has_more: false } }), stderr: "" }
    },
  })
  const config: Record<string, any> = { mcp: { "codebase-memory-mcp": { type: "local", command: ["cbm"] } } }
  try {
    await Promise.race([
      hooks.config!(config as any),
      Bun.sleep(500).then(() => { throw new Error("config blocked on registration") }),
    ])
    await Bun.sleep(20)
    expect(indexingPending).toBe(true)
    expect(config.skills.paths).toContain(skillsDir)
    expect(config.command[`${namespace}:pr-open`]).toBeDefined()
    expect(config.agent["tdd-red"]).toBeDefined()
    const output = { args: { name: `${namespace}:iwe-plan` } }
    await hooks["tool.execute.before"]!({ tool: "skill", sessionID: "s", callID: "c" }, output)
    expect(output.args.name).toBe("iwe-plan")
  } finally { release() }
})

test("registration failures reach the OpenCode logging client", async () => {
  const messages: any[] = []
  const hooks = await bridge(root, {
    directory: root,
    client: { app: { log: async (entry: unknown) => { messages.push(entry) } } },
  } as any, { run: async () => { throw new Error("executable unavailable") } })
  const config: Record<string, any> = { mcp: { "codebase-memory-mcp": { type: "local", command: ["cbm"] } } }
  await hooks.config!(config as any)
  await Bun.sleep(20)
  expect(config.command[`${namespace}:pr-open`]).toBeDefined()
  expect(messages[0].body).toMatchObject({ service: "agentdev", level: "warn" })
  expect(messages[0].body.message).toContain("executable unavailable")
})

/** A fake OpenCode v2 plugin ctx whose editors and hooks record what the bridge registers. */
function fakeV2(options: { registration?: Promise<unknown>; agentSystem?: Record<string, string>; mcp?: Record<string, any> } = {}) {
  const registration = options.registration ?? Promise.resolve({ dispose: async () => {} })
  const transforms: Record<string, (editor: any) => void> = {}
  const hooks: Record<string, (input: any) => unknown> = {}
  const prompts: any[] = []
  const skills = new Map<string, any>()
  const commands = new Map<string, any>()
  const agents = new Map<string, any>()
  const transform = (domain: string) => (callback: (editor: any) => void) => {
    transforms[domain] = callback
    return registration
  }
  const hook = (domain: string) => (name: string, callback: (input: any) => unknown) => {
    hooks[`${domain}.${name}`] = callback
    return registration
  }
  const ctx = {
    location: { directory: root, project: { directory: root } },
    skill: { transform: transform("skill") },
    command: { transform: transform("command") },
    agent: {
      transform: transform("agent"),
      get: async ({ agentID }: { agentID: string }) => ({
        data: { ...agents.get(agentID), system: options.agentSystem?.[agentID] ?? agents.get(agentID)?.system },
      }),
    },
    tool: { hook: hook("tool") },
    session: { hook: hook("session"), prompt: async (input: unknown) => { prompts.push(input) } },
    permission: { hook: hook("permission") },
    mcp: { transform: transform("mcp") },
  }
  const mcp = structuredClone(options.mcp ?? {})
  const apply = () => {
    transforms.mcp?.({ get: (name: string) => mcp[name] })
    transforms.skill?.({ get: (id: string) => skills.get(id), add: (s: any) => skills.set(s.id, s) })
    transforms.command?.({ add: (c: any) => commands.set(c.name, c) })
    transforms.agent?.({
      get: (id: string) => agents.get(id),
      update: (id: string, fn: (a: any) => void) => {
        const agent = agents.get(id) ?? { id, name: id, mode: "primary", permissions: [{ action: "*", resource: "*", effect: "allow" }] }
        fn(agent)
        agents.set(id, agent)
      },
    })
  }
  return { ctx, transforms, hooks, prompts, skills, commands, agents, mcp, apply }
}

function setUp(options?: Parameters<typeof fakeV2>[0], adapters?: Parameters<typeof setupBridge>[2]) {
  const fake = fakeV2(options)
  setupBridge(root, fake.ctx as any, adapters)
  fake.apply()
  return fake
}

function v2Denied(meta: Record<string, unknown>): string[] {
  const granted = new Set(claudeTools(meta).flatMap((tool) => V2_TOOL_ACTIONS[tool]))
  return V2_SUBAGENT_ACTIONS.filter((action) => !granted.has(action))
}

const v2Tools = ["shell", "read", "edit", "write", "patch", "grep", "glob", "websearch", "webfetch", "subagent", "skill", "question", "execute", "browser"]

describe("v2 setup", () => {
  test("adds every catalog skill under its bare name with its SKILL.md and body", () => {
    const { skills: added } = setUp()
    expect(added.size).toBe(skills.length)
    for (const { dir, meta } of skills) {
      const skill = added.get(String(meta.name))
      expect(skill.name).toBe(meta.name)
      expect(skill.description).toBe(meta.description)
      expect(skill.path).toBe(path.join(dir, "SKILL.md"))
      expect(skill.content.length).toBeGreaterThan(0)
      expect(skill.content).not.toStartWith("---")
      expect(skill.autoinvoke === false).toBe(meta["disable-model-invocation"] === true)
    }
  })

  test("adds every skill as a namespaced command that re-prompts with the complete invocation", async () => {
    const { commands, prompts } = setUp()
    for (const { meta } of skills) {
      const command = commands.get(`${namespace}:${meta.name}`)
      expect(command.description).toBe(meta.description)
    }
    const files = [{
      uri: "file:///critical.ts",
      mention: { start: 13, end: 25, text: "@critical.ts" },
    }]
    const agentsRef = [{
      name: "tdd-red",
      mention: { start: 26, end: 34, text: "@tdd-red" },
    }]
    const skillsRef = [{
      id: "iwe-plan",
      name: "iwe-plan",
      mention: { start: 35, end: 44, text: "/iwe-plan" },
    }]
    await commands.get(`${namespace}:iwe-implement`).execute({
      sessionID: "ses_1",
      prompt: {
        text: "fix critical @critical.ts @tdd-red /iwe-plan\nwithout changing behavior",
        files,
        agents: agentsRef,
        skills: skillsRef,
      },
      delivery: "steer",
    })
    await commands.get(`${namespace}:iwe-ship`).execute({
      sessionID: "ses_2",
      prompt: { text: "" },
      delivery: "queue",
    })
    expect(prompts).toEqual([{
      sessionID: "ses_1",
      text: "/agentdev:iwe-implement fix critical @critical.ts @tdd-red /iwe-plan\nwithout changing behavior",
      files: [{
        uri: "file:///critical.ts",
        mention: { start: 37, end: 49, text: "@critical.ts" },
      }],
      agents: [{
        name: "tdd-red",
        mention: { start: 50, end: 58, text: "@tdd-red" },
      }],
      skills: [{
        id: "iwe-plan",
        name: "iwe-plan",
        mention: { start: 59, end: 68, text: "/iwe-plan" },
      }, { id: "iwe-implement" }],
      delivery: "steer",
    }, {
      sessionID: "ses_2",
      text: "/agentdev:iwe-ship",
      files: undefined,
      agents: undefined,
      skills: [{ id: "iwe-ship" }],
      delivery: "queue",
    }])
    expect(prompts).toHaveLength(2)
    expect(prompts[0].text).not.toContain("# Implement a plan")
    expect(files[0].mention).toEqual({ start: 13, end: 25, text: "@critical.ts" })
    expect(agentsRef[0].mention).toEqual({ start: 26, end: 34, text: "@tdd-red" })
    expect(skillsRef[0].mention).toEqual({ start: 35, end: 44, text: "/iwe-plan" })
  })

  test("maps every Claude tool a catalog agent uses", () => {
    for (const { meta } of agents) {
      for (const tool of claudeTools(meta)) expect(V2_TOOL_ACTIONS).toHaveProperty(tool)
    }
  })

  test("updates every agent as a subagent with its prompt and adds no permission rule", () => {
    const { agents: added } = setUp()
    for (const { stem, meta } of agents) {
      const agent = added.get(stem)
      expect(agent.mode).toBe("subagent")
      expect(agent.description).toBe(meta.description)
      expect(agent.system.length).toBeGreaterThan(0)
      expect(agent.permissions).toEqual([{ action: "*", resource: "*", effect: "allow" }])
    }
  })

  test("withholds each catalog agent's undeclared tools from the model", async () => {
    const { hooks } = setUp()
    for (const { stem, meta } of agents) {
      const context = { agent: stem, tools: Object.fromEntries(v2Tools.map((t) => [t, { description: t, input: {} }])) }
      await hooks["session.context"](context)
      const denied = v2Denied(meta)
      expect(Object.keys(context.tools).sort()).toEqual(v2Tools.filter((t) => !denied.includes(t)).sort())
    }
  })

  test("tdd-red is refused web, subagent, skill, and question calls and keeps shell's approval", async () => {
    const { hooks } = setUp()
    const evaluate = async (action: string, effect = "allow") => {
      const input = { sessionID: "s", agent: "tdd-red", action, resources: ["*"], effect }
      await hooks["permission.evaluate"](input)
      return input.effect
    }
    for (const action of ["webfetch", "websearch", "subagent", "skill", "question"]) {
      expect(await evaluate(action)).toBe("deny")
    }
    expect(await evaluate("shell", "ask")).toBe("ask")
    expect(await evaluate("read")).toBe("allow")
    expect(await evaluate("execute")).toBe("allow")
    expect(await evaluate("browser", "deny")).toBe("deny")
  })

  test("leaves non-catalog agents and user-replaced catalog agents unlimited", async () => {
    const { hooks } = setUp({ agentSystem: { "tdd-red": "the user's own prompt" } })
    for (const agent of ["tdd-red", "build"]) {
      const context = { agent, tools: Object.fromEntries(v2Tools.map((t) => [t, { description: t, input: {} }])) }
      await hooks["session.context"](context)
      expect(Object.keys(context.tools)).toEqual(v2Tools)
      const input = { sessionID: "s", agent, action: "webfetch", resources: ["*"], effect: "allow" }
      await hooks["permission.evaluate"](input)
      expect(input.effect).toBe("allow")
    }
  })

  test("the execute.before hook strips the namespace from a skill call only", async () => {
    const { hooks } = setUp()
    const call = async (tool: string, input: Record<string, unknown>) => {
      const event = { tool, sessionID: "s", agent: "build", messageID: "m", id: "c", input: { ...input } }
      await hooks["tool.execute.before"](event)
      return event.input
    }
    expect(await call("skill", { id: `${namespace}:iwe-plan` })).toEqual({ id: "iwe-plan" })
    expect(await call("skill", { id: "iwe-plan" })).toEqual({ id: "iwe-plan" })
    const other = { id: `${namespace}:iwe-plan`, command: `${namespace}:iwe-plan` }
    expect(await call("shell", other)).toEqual(other)
  })

  test("setup returns without waiting on any registration", async () => {
    const fake = fakeV2({ registration: new Promise(() => {}) })
    const result = await Promise.race([
      Promise.resolve(setupBridge(root, fake.ctx as any)).then(() => "returned"),
      Bun.sleep(500).then(() => "blocked"),
    ])
    expect(result).toBe("returned")
    expect(Object.keys(fake.transforms).sort()).toEqual(["agent", "command", "mcp", "skill"])
    expect(Object.keys(fake.hooks).sort()).toEqual(["permission.evaluate", "session.context", "tool.execute.before"])
  })
})

const cbmEntry = { type: "local", command: ["cbm"], environment: { CBM_CACHE_DIR: "/fixture" } }

describe("v2 workspace registration", () => {
  test("registers ctx.location.directory with the configured CBM entry and changes no MCP config", async () => {
    const commands: string[][] = []
    const fake = setUp({ mcp: { "codebase-memory-mcp": cbmEntry } }, {
      run: async command => {
        commands.push(command)
        return command[0] === "git"
          ? { exitCode: 0, stdout: root, stderr: "" }
          : { exitCode: 0, stdout: JSON.stringify({ structuredContent: { projects: [{ root_path: root }], has_more: false } }), stderr: "" }
      },
    })
    await Bun.sleep(20)
    expect(commands[0]).toEqual(["git", "-C", root, "rev-parse", "--show-toplevel"])
    expect(commands[1]).toEqual(["cbm", "cli", "--json", "list_projects", "--format", "json"])
    expect(fake.mcp).toEqual({ "codebase-memory-mcp": cbmEntry })
  })

  test("a v2 entry with disabled: true is a quiet skip", async () => {
    const commands: string[][] = []
    const logs: string[] = []
    setUp({ mcp: { "codebase-memory-mcp": { ...cbmEntry, disabled: true } } }, {
      run: async command => { commands.push(command); return { exitCode: 0, stdout: "", stderr: "" } },
      log: async message => { logs.push(message) },
    })
    await Bun.sleep(20)
    expect(commands).toEqual([])
    expect(logs).toEqual([])
  })

  test("setup returns while CBM registration is still pending", async () => {
    let release!: () => void
    const pending = new Promise<void>(resolve => { release = resolve })
    let started = false
    const fake = fakeV2({ mcp: { "codebase-memory-mcp": cbmEntry } })
    try {
      const result = await Promise.race([
        Promise.resolve(setupBridge(root, fake.ctx as any, {
          run: async () => { started = true; await pending; return { exitCode: 1, stdout: "", stderr: "" } },
        })).then(() => { fake.apply(); return "returned" }),
        Bun.sleep(500).then(() => "blocked"),
      ])
      expect(result).toBe("returned")
      await Bun.sleep(20)
      expect(started).toBe(true)
      expect(fake.commands.get(`${namespace}:pr-open`)).toBeDefined()
    } finally { release() }
  })

  test("a registration failure reaches the v2 log adapter", async () => {
    const logs: string[] = []
    setUp({ mcp: { "codebase-memory-mcp": cbmEntry } }, {
      run: async () => { throw new Error("executable unavailable") },
      log: async message => { logs.push(message) },
    })
    await Bun.sleep(20)
    expect(logs).toHaveLength(1)
    expect(logs[0]).toContain("executable unavailable")
  })
})

describe("v2 effect export", () => {
  /** Fakes of the two host modules the effect export requires. */
  function hostModules() {
    const ran: { context: unknown; effect: any }[] = []
    const hostContext = { host: true }
    const plugins: any[] = []
    const Effect = {
      contextWith: (fn: (context: unknown) => unknown) => fn(hostContext),
      logWarning: (message: string) => ({ message, pipe(f: (e: any) => any) { return f(this) } }),
      annotateLogs: (annotations: Record<string, unknown>) => (effect: any) => ({ ...effect, annotations }),
      runPromiseWith: (context: unknown) => async (effect: any) => { ran.push({ context, effect }) },
    }
    const fromPromise = (plugin: any) => {
      plugins.push(plugin)
      return { effect: (ctx: unknown) => { plugin.setup(ctx); return "host effect" } }
    }
    const load = (name: string) => {
      if (name === "effect") return { Effect }
      if (name === "@opencode/plugin/promise/adapter") return { fromPromise }
      throw new Error(`unexpected module ${name}`)
    }
    return { ran, hostContext, plugins, load }
  }

  test("runs the v2 setup through fromPromise inside the host's Effect context", () => {
    const host = hostModules()
    const fake = fakeV2()
    expect(v2Effect(root, fake.ctx as any, host.load)).toBe("host effect")
    fake.apply()
    expect(host.plugins[0].id).toBe(plugin.id)
    expect(fake.commands.get(`${namespace}:pr-open`)).toBeDefined()
  })

  test("logs CBM warnings at warning level, annotated service agentdev, in the host's context", async () => {
    const host = hostModules()
    const fake = fakeV2({ mcp: { "codebase-memory-mcp": cbmEntry } })
    v2Effect(root, fake.ctx as any, host.load, { run: async () => { throw new Error("executable unavailable") } })
    fake.apply()
    await Bun.sleep(20)
    expect(host.ran).toHaveLength(1)
    expect(host.ran[0].context).toBe(host.hostContext)
    expect(host.ran[0].effect.message).toContain("executable unavailable")
    expect(host.ran[0].effect.annotations).toEqual({ service: "agentdev" })
  })
})
