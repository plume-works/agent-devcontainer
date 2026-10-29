// Host checks for the bridge on OpenCode v2: catalog agent tool limits under
// full access, driven by a local mock model, and CBM warnings in opencode.log.
// OPENCODE_BIN selects the v2 executable.
import assert from "node:assert/strict"
import { spawn, spawnSync } from "node:child_process"
import { closeSync, mkdirSync, mkdtempSync, openSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import path from "node:path"

const pluginRoot = path.resolve(import.meta.dir, "../..")
const opencode = process.env.OPENCODE_BIN ?? Bun.which("opencode")
assert(opencode, "An OpenCode v2 executable is required; set OPENCODE_BIN")
const version = spawnSync(opencode, ["--version"], { encoding: "utf8" })
assert.match(version.stdout, /(^|[^\d.])2\.\d+\.\d+/, `OpenCode v2 is required, found: ${version.stdout}`)

const gitRoot = spawnSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf8" }).stdout.trim()
const scratch = "/tmp/agentdev-tests"
mkdirSync(scratch, { recursive: true })
const fixture = mkdtempSync(path.join(scratch, "oc-limits-"))
const workspace = path.join(fixture, "ws")
const configDir = path.join(fixture, "home/.config/opencode")
for (const dir of [workspace, configDir]) mkdirSync(dir, { recursive: true })
spawnSync("git", ["init", "-q", workspace])
writeFileSync(path.join(workspace, "notes.txt"), "catalog limits fixture\n")
const password = "agent-limits"
const env: NodeJS.ProcessEnv = { ...process.env, HOME: path.join(fixture, "home"), OPENCODE_SERVER_PASSWORD: password, OPENAI_API_KEY: "mock" }
for (const key of ["XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME", "OPENCODE_CONFIG", "OPENCODE_CONFIG_CONTENT", "OPENCODE_CONFIG_DIR"]) delete env[key]

interface ModelRequest { tools: string[]; outputs: string[] }
const requests: ModelRequest[] = []

function sse(events: Record<string, unknown>[]): Response {
  const body = events.map(event => `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`).join("")
  return new Response(body, { headers: { "content-type": "text/event-stream" } })
}

function reply(item: Record<string, unknown>): Response {
  const response = { id: `resp_${requests.length}`, object: "response", created_at: 0, model: "gpt-5", status: "in_progress", output: [] }
  return sse([
    { type: "response.created", response },
    { type: "response.output_item.added", output_index: 0, item: { ...item, status: "in_progress" } },
    { type: "response.output_item.done", output_index: 0, item: { ...item, status: "completed" } },
    { type: "response.completed", response: { ...response, status: "completed", output: [item], usage: { input_tokens: 1, output_tokens: 1, total_tokens: 2 } } },
  ])
}

// A user message "call <tool> <json>" makes the model call that tool once;
// any later turn ends with text.
const model = Bun.serve({
  hostname: "127.0.0.1",
  port: 0,
  async fetch(request) {
    const url = new URL(request.url)
    if (url.pathname === "/page") return new Response("mock page")
    if (request.method !== "POST") return new Response("not found", { status: 404 })
    const body = await request.json() as { tools?: { name?: string }[]; input?: Record<string, any>[] }
    const input = body.input ?? []
    const outputs = input.filter(item => item.type === "function_call_output").map(item => JSON.stringify(item.output))
    // Title generation runs without tools; only agent turns are recorded.
    if (body.tools?.length) requests.push({ tools: body.tools.map(tool => String(tool.name)), outputs })
    const content = input.findLast(item => item.role === "user")?.content ?? []
    const text = content.find((part: { type: string }) => part.type === "input_text")?.text ?? ""
    const call = /^call (\w+) (\{.*\})$/s.exec(text)
    if (outputs.length === 0 && call) {
      return reply({ type: "function_call", id: "fc_1", call_id: `call_${requests.length}`, name: call[1], arguments: call[2] })
    }
    return reply({ type: "message", id: "msg_1", role: "assistant", content: [{ type: "output_text", text: "done", annotations: [] }] })
  },
})

function configure(extra: Record<string, unknown> = {}) {
  writeFileSync(path.join(configDir, "opencode.json"), JSON.stringify({
    plugin: [path.join(pluginRoot, ".opencode-plugin")],
    permission: { "*": "allow", external_directory: "allow" },
    model: "openai/gpt-5",
    provider: { openai: { options: { baseURL: `http://127.0.0.1:${model.port}/v1`, apiKey: "mock" } } },
    ...extra,
  }))
}

let host: ReturnType<typeof spawn> | undefined
let address = ""

async function startHost(name: string) {
  const reservation = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: () => new Response() })
  const port = reservation.port
  reservation.stop(true)
  address = `http://127.0.0.1:${port}`
  const log = path.join(fixture, `host-${name}.log`)
  const fd = openSync(log, "w")
  host = spawn(opencode!, ["serve", "--hostname", "127.0.0.1", "--port", String(port)], { cwd: workspace, env, detached: true, stdio: ["ignore", fd, fd] })
  closeSync(fd)
  const deadline = Date.now() + 30_000
  while (Date.now() < deadline) {
    assert(host.exitCode === null, `OpenCode exited: ${readFileSync(log, "utf8")}`)
    try {
      if ((await fetch(address, { headers: auth(), signal: AbortSignal.timeout(500) })).ok) return
    } catch (error) {
      if (host.exitCode !== null) throw error
    }
    await Bun.sleep(200)
  }
  throw new Error(`OpenCode start timeout: ${readFileSync(log, "utf8")}`)
}

function stopHost() {
  if (host?.pid && host.exitCode === null) process.kill(-host.pid, "SIGKILL")
  host = undefined
}

function auth() {
  return { authorization: `Basic ${Buffer.from(`opencode:${password}`).toString("base64")}` }
}

function api(operation: string, params: Record<string, string> = {}, data?: unknown) {
  const args = ["api", "--server", address, operation, ...Object.entries(params).flatMap(([k, v]) => ["--param", `${k}=${v}`])]
  if (data !== undefined) args.push("-d", JSON.stringify(data))
  const result = spawnSync(opencode!, args, { cwd: workspace, env, encoding: "utf8", timeout: 60_000 })
  assert.equal(result.status, 0, `${operation}: ${result.stderr}\n${result.stdout}`)
  return JSON.parse(result.stdout).data
}

// The first requests after start can precede plugin activation.
async function until<T>(read: () => T, ready: (value: T) => boolean, what: string): Promise<T> {
  const deadline = Date.now() + 30_000
  for (;;) {
    const value = read()
    if (ready(value)) return value
    assert(Date.now() < deadline, `Timed out waiting for ${what}`)
    await Bun.sleep(300)
  }
}

/** Run one turn of `agent` that calls `tool`; return the offered tools and the tool's result. */
async function turn(agent: string, tool: string, args: Record<string, unknown>) {
  const session = api("session.create", {}, { agent })
  const before = requests.length
  api("session.prompt", { sessionID: session.id }, { text: `call ${tool} ${JSON.stringify(args)}` })
  await until(() => requests.length, count => count >= before + 2, `${agent}'s ${tool} turn`)
  const [first, second] = requests.slice(before)
  return { tools: first.tools, result: second.outputs.join("\n") }
}

try {
  configure()
  await startHost("catalog")
  await until(() => api("agent.list") as { id: string }[], list => list.some(a => a.id === "tdd-red"), "catalog agents")

  const fetched = await turn("tdd-red", "webfetch", { url: `http://127.0.0.1:${model.port}/page`, format: "text" })
  assert(!fetched.tools.includes("webfetch"), `tdd-red is offered webfetch: ${fetched.tools}`)
  assert(fetched.tools.includes("read"), `tdd-red lost read: ${fetched.tools}`)
  assert.match(fetched.result, /Tool is not available for this request: webfetch|Permission denied: webfetch/, `webfetch was not refused: ${fetched.result}`)
  assert.doesNotMatch(fetched.result, /mock page/, "webfetch ran for tdd-red")

  const read = await turn("tdd-red", "read", { path: path.join(workspace, "notes.txt") })
  assert.match(read.result, /catalog limits fixture/, `tdd-red's read did not run: ${read.result}`)
  console.log("ok - tdd-red is limited to its declared tools under full access")
  stopHost()

  const userSkill = path.join(configDir, "skills/iwe-plan")
  mkdirSync(userSkill, { recursive: true })
  writeFileSync(path.join(userSkill, "SKILL.md"), "---\nname: iwe-plan\ndescription: the user's iwe-plan\n---\nuser skill body\n")
  configure({
    agent: { "tdd-red": { description: "the user's tdd-red", prompt: "the user's own prompt", mode: "subagent" } },
    command: { "agentdev:pr-open": { description: "the user's pr-open", template: "mine" } },
  })
  await startHost("user")
  const commands = await until(() => api("command.list") as { name: string; description?: string }[],
    list => list.some(c => c.name === "agentdev:pr-gen-description"), "catalog commands")
  assert.equal(commands.find(c => c.name === "agentdev:pr-open")?.description, "the user's pr-open")
  const skill = (api("skill.list") as { id: string; path: string }[]).find(s => s.id === "iwe-plan")
  assert.equal(skill?.path, path.join(userSkill, "SKILL.md"), "the bridge's iwe-plan replaced the user's")
  const replaced = await turn("tdd-red", "webfetch", { url: `http://127.0.0.1:${model.port}/page`, format: "text" })
  assert(replaced.tools.includes("webfetch"), `the user's tdd-red is not offered webfetch: ${replaced.tools}`)
  assert.match(replaced.result, /mock page/, `the user's tdd-red could not fetch: ${replaced.result}`)
  console.log("ok - the user's agent, command, and skill replace the catalog's")
  stopHost()

  rmSync(userSkill, { recursive: true })
  configure({ mcp: { "codebase-memory-mcp": { type: "local", command: [path.join(fixture, "missing-cbm")], enabled: true } } })
  await startHost("cbm")
  api("agent.list") // plugins activate for a directory on its first request
  const opencodeLog = path.join(fixture, "home/.local/share/opencode/log/opencode.log")
  const warning = await until(() => readFileSync(opencodeLog, "utf8").split("\n").find(line =>
    line.includes("level=WARN") && line.includes("service=agentdev") && line.includes("CBM workspace registration failed")),
  line => line !== undefined, "the bridge's CBM warning in opencode.log")
  assert(warning)
  console.log("ok - a CBM registration failure is logged to opencode.log")
} finally {
  stopHost()
  model.stop(true)
}
