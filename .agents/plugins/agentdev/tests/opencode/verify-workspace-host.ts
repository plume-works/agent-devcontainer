import assert from "node:assert/strict"
import { spawn, spawnSync } from "node:child_process"
import { cpSync, existsSync, mkdirSync, mkdtempSync, openSync, closeSync, readFileSync, readlinkSync, rmSync, writeFileSync } from "node:fs"
import os from "node:os"
import path from "node:path"

const pluginRoot = path.resolve(import.meta.dir, "../..")
const opencode = Bun.which("opencode")
const cbm = Bun.which("codebase-memory-mcp")
assert(opencode && cbm, "Installed opencode and codebase-memory-mcp executables are required")
const sdkDir = process.env.OPENCODE_TEST_SDK_DIR ?? process.env.OPENCODE_CONFIG_DIR ?? path.join(process.env.XDG_CONFIG_HOME ?? path.join(os.homedir(), ".config"), "opencode")
const version = spawnSync(opencode, ["--version"], { encoding: "utf8" })
assert.equal(version.status, 0, "Cannot read installed OpenCode version")
const hostVersion = version.stdout.trim()
for (const file of ["package.json", "package-lock.json", "node_modules/@opencode-ai/plugin/package.json"]) {
  assert(existsSync(path.join(sdkDir, file)), `SDK seed missing ${file}; set OPENCODE_TEST_SDK_DIR to a provisioned OpenCode config directory`)
}
const manifest = JSON.parse(readFileSync(path.join(sdkDir, "package.json"), "utf8"))
const lock = JSON.parse(readFileSync(path.join(sdkDir, "package-lock.json"), "utf8"))
const sdk = JSON.parse(readFileSync(path.join(sdkDir, "node_modules/@opencode-ai/plugin/package.json"), "utf8"))
assert.equal(sdk.version, hostVersion, "SDK seed must match the installed OpenCode version")
assert.equal(lock.packages?.[""]?.dependencies?.["@opencode-ai/plugin"], hostVersion, "SDK lockfile must match the host version")
for (const section of ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]) {
  for (const name of Object.keys(manifest[section] ?? {})) {
    assert(lock.packages?.[""]?.[section]?.[name], `SDK lockfile does not cover ${name}`)
  }
}

const parentFlag = process.argv.indexOf("--parent-mount")
if (parentFlag === -1) {
  const child = spawnSync("unshare", ["--mount", "--propagation", "private", "bash", "-c",
    'mount -t tmpfs tmpfs /tmp && exec "$@"', "verify-workspace-host", process.execPath,
    import.meta.path, "--parent-mount", readlinkSync("/proc/self/ns/mnt")], { stdio: "inherit" })
  if (child.error) throw child.error
  process.exit(child.status ?? 1)
}
assert.notEqual(readlinkSync("/proc/self/ns/mnt"), process.argv[parentFlag + 1], "A private mount namespace is required")
assert(readFileSync("/proc/self/mountinfo", "utf8").split("\n").some(line => line.includes(" /tmp ") && line.includes(" - tmpfs ")), "The test daemon endpoint must be isolated on private tmpfs")

const gitRoot = spawnSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf8" })
assert.equal(gitRoot.status, 0, "Run inside the repository being verified")
const scratch = path.join(gitRoot.stdout.trim(), ".tmp")
mkdirSync(scratch, { recursive: true })
const fixture = mkdtempSync(path.join(scratch, "oc-host-"))
const configDir = path.join(fixture, "config/opencode")
const env: NodeJS.ProcessEnv = { ...process.env,
  HOME: path.join(fixture, "home"), XDG_CONFIG_HOME: path.join(fixture, "config"),
  XDG_DATA_HOME: path.join(fixture, "data"), XDG_CACHE_HOME: path.join(fixture, "cache"),
  XDG_STATE_HOME: path.join(fixture, "state"), OPENCODE_CONFIG_DIR: configDir,
  OPENCODE_DISABLE_DEFAULT_PLUGINS: "1", OPENCODE_DISABLE_EXTERNAL_SKILLS: "1",
  OPENCODE_DISABLE_CLAUDE_CODE_SKILLS: "1", OPENCODE_DISABLE_MODELS_FETCH: "1",
  npm_config_offline: "true", npm_config_registry: "http://127.0.0.1:9",
  CBM_CACHE_DIR: path.join(fixture, "cbm"), CBM_ALLOWED_ROOT: fixture,
}
for (const key of ["OPENCODE_CONFIG", "OPENCODE_CONFIG_CONTENT", "OPENCODE_SERVER_PASSWORD", "OPENCODE_SERVER_USERNAME", "OPENCODE_PURE", "OPENCODE_DISABLE_PROJECT_CONFIG"]) delete env[key]
for (const dir of [env.HOME!, env.XDG_DATA_HOME!, env.XDG_CACHE_HOME!, env.XDG_STATE_HOME!, env.CBM_CACHE_DIR!, configDir]) mkdirSync(dir, { recursive: true })
for (const name of ["package.json", "package-lock.json", "node_modules"]) cpSync(path.join(sdkDir, name), path.join(configDir, name), { recursive: true, dereference: true })

let sequence = 0
let daemonStarted = false
let host: ReturnType<typeof spawn> | undefined
let hostLog = ""
let address = ""

function terminate(child: ReturnType<typeof spawn>) {
  if (child.exitCode !== null || child.signalCode !== null || !child.pid) return
  try { process.kill(-child.pid, "SIGKILL") } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ESRCH") throw error
  }
}

async function run(command: string[], cwd = fixture, allowError = false) {
  const log = path.join(fixture, `command-${sequence++}`)
  const out = openSync(`${log}.out`, "w")
  const err = openSync(`${log}.err`, "w")
  const child = spawn(command[0], command.slice(1), { cwd, env, detached: true, stdio: ["ignore", out, err] })
  closeSync(out)
  closeSync(err)
  const timer = setTimeout(() => terminate(child), 60_000)
  let code: number | null
  try {
    code = await new Promise<number | null>((resolve, reject) => {
      child.once("error", reject)
      child.once("exit", resolve)
    })
  } finally { clearTimeout(timer) }
  const stdout = readFileSync(`${log}.out`, "utf8")
  const stderr = readFileSync(`${log}.err`, "utf8")
  if (!allowError) assert.equal(code, 0, `${command.join(" ")} failed: ${stderr.slice(-4000)}\n${stdout.slice(-4000)}`)
  return { code, stdout, stderr }
}

async function cli(tool: string, args: string[] = [], allowAbsent = false) {
  const result = await run([cbm!, "cli", "--json", tool, ...args], fixture, true)
  const envelope = JSON.parse(result.stdout)
  const data = envelope.structuredContent
  if (allowAbsent && envelope.isError && String(data?.error).includes("no index job or index is known")) return { state: "absent" }
  assert.equal(result.code, 0, `CBM ${tool}: ${result.stdout}\n${result.stderr}`)
  assert.notEqual(envelope.isError, true, `CBM ${tool}: ${result.stdout}`)
  assert(data && typeof data === "object", `CBM ${tool} returned no structuredContent`)
  return data
}

function configure(mode: "enabled" | "disabled" | "unavailable") {
  writeFileSync(path.join(configDir, "opencode.json"), JSON.stringify({
    $schema: "https://opencode.ai/config.json", plugin: [path.join(pluginRoot, ".opencode-plugin")],
    mcp: { "codebase-memory-mcp": { type: "local", command: [mode === "unavailable" ? path.join(fixture, "missing-cbm") : cbm],
      enabled: mode !== "disabled", environment: { CBM_CACHE_DIR: env.CBM_CACHE_DIR, CBM_ALLOWED_ROOT: fixture } } },
  }))
}

async function startHost(mode: "enabled" | "disabled" | "unavailable") {
  configure(mode)
  const reservation = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: () => new Response() })
  const port = reservation.port
  reservation.stop(true)
  address = `http://127.0.0.1:${port}`
  hostLog = path.join(fixture, `host-${mode}.log`)
  const fd = openSync(hostLog, "w")
  host = spawn(opencode!, ["--print-logs", "--log-level", "DEBUG", "serve", "--hostname", "127.0.0.1", "--port", String(port)], { cwd: fixture, env, detached: true, stdio: ["ignore", fd, fd] })
  closeSync(fd)
  const deadline = Date.now() + 20_000
  while (Date.now() < deadline) {
    assert(host.exitCode === null, `OpenCode exited: ${readFileSync(hostLog, "utf8")}`)
    try {
      if ((await fetch(`${address}/global/health`, { signal: AbortSignal.timeout(500) })).ok) return
    } catch (error) {
      if (host.exitCode !== null) throw error
    }
    await Bun.sleep(100)
  }
  throw new Error(`OpenCode health timeout: ${readFileSync(hostLog, "utf8")}`)
}

async function stopHost() {
  if (!host) return
  const current = host
  if (current.exitCode === null && current.signalCode === null) {
    const exited = new Promise(resolve => current.once("exit", resolve))
    terminate(current)
    await exited
  }
  host = undefined
}

async function catalog(root: string) {
  const start = Date.now()
  const result = await fetch(`${address}/config?directory=${encodeURIComponent(root)}`, { signal: AbortSignal.timeout(20_000) })
  assert.equal(result.status, 200, await result.clone().text())
  const config = await result.json() as any
  const ms = Date.now() - start
  assert(config.command?.["agentdev:pr-open"], "Host is missing catalog commands")
  assert(config.agent?.["tdd-red"], "Host is missing catalog agents")
  const skills = await run([opencode!, "debug", "skill"], root)
  assert(skills.stdout.includes("iwe-plan"), "Host is missing catalog skills")
  const debug = await run([opencode!, "debug", "config"], root)
  assert(debug.stdout.includes("agentdev:pr-open"), "Debug config is missing catalog commands")
  return ms
}

async function indexed(root: string) {
  const deadline = Date.now() + 60_000
  while (Date.now() < deadline) {
    const job = await cli("index_repository", ["--repo-path", root, "--status", "true"], true)
    assert(!["failed", "cancelled"].includes(job.state), JSON.stringify(job))
    if (job.state === "succeeded") return job
    await Bun.sleep(100)
  }
  throw new Error(`Index completion timeout: ${readFileSync(hostLog, "utf8")}`)
}

async function repository(name: string) {
  const root = path.join(fixture, name)
  await run(["git", "init", root])
  writeFileSync(path.join(root, "sample.py"), 'def hello():\n    return "fixture"\n')
  return root
}

async function roots() {
  const data = await cli("list_projects", ["--format", "json"])
  assert.equal(data.has_more, false, "Unexpected project pagination in empty test daemon")
  return data.projects.map((project: any) => project.root_path).sort()
}

let cleaning: Promise<void> | undefined
function cleanup() {
  return cleaning ??= (async () => {
    await stopHost()
    if (daemonStarted) await run([cbm!, "daemon", "stop"])
    rmSync(fixture, { recursive: true, force: true })
  })()
}
for (const signal of ["SIGINT", "SIGTERM"] as const) process.once(signal, () => {
  void cleanup().then(() => process.exit(signal === "SIGINT" ? 130 : 143)).catch(error => { console.error(error); process.exit(1) })
})

try {
  await run([cbm!, "daemon", "start"])
  daemonStarted = true
  assert.deepEqual(await roots(), [], "The isolated daemon must begin empty")
  await startHost("enabled")
  const first = await repository("first")
  const second = await repository("second")
  for (const root of [first, second]) {
    const configMs = await catalog(root)
    await indexed(root)
    assert(!existsSync(path.join(root, ".codebase-memory/graph.db.zst")), "Repository snapshot persistence was enabled")
    console.log(`PASS ${path.basename(root)}: catalog available in ${configMs} ms; background indexing succeeded`)
  }
  const before = await indexed(first)
  const nested = path.join(first, "nested")
  mkdirSync(nested)
  await catalog(nested)
  await Bun.sleep(500)
  assert.deepEqual(await indexed(first), before, "Subdirectory reopening started a new job")
  assert.deepEqual(await roots(), [first, second].sort())
  console.log("PASS subdirectory: original job and both exact roots retained")
  await stopHost()
  for (const mode of ["disabled", "unavailable"] as const) {
    await startHost(mode)
    const root = await repository(mode)
    await catalog(root)
    const deadline = Date.now() + 5000
    while (mode === "unavailable" && !readFileSync(hostLog, "utf8").includes("CBM workspace registration failed") && Date.now() < deadline) await Bun.sleep(100)
    if (mode === "disabled") await Bun.sleep(300)
    assert.equal(readFileSync(hostLog, "utf8").includes("CBM workspace registration failed"), mode === "unavailable")
    assert.deepEqual(await roots(), [first, second].sort(), `${mode}: an unindexed root was registered`)
    console.log(`PASS ${mode}: catalog usable; ${mode === "disabled" ? "quiet skip" : "registration warning"}; no index submitted`)
    await stopHost()
  }
} catch (error) {
  if (hostLog && existsSync(hostLog)) console.error(readFileSync(hostLog, "utf8").slice(-8000))
  throw error
} finally { await cleanup() }
console.log(`PASS cleanup: test host, daemon, and fixture resources removed (OpenCode ${hostVersion})`)
