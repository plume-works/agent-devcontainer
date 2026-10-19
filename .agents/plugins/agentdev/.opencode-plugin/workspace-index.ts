import { spawn } from "node:child_process"
import { realpath } from "node:fs/promises"

interface CommandResult {
  exitCode: number
  stdout: string
  stderr: string
}

export interface WorkspaceConfig {
  mcp?: Record<string, unknown>
}

export interface RegistrationAdapters {
  run: (command: string[], env: NodeJS.ProcessEnv, options?: { captureOutput?: boolean }) => Promise<CommandResult>
  log: (message: string) => Promise<unknown>
}

/** Execute without a shell, bounding runtime and combined captured output. */
export function runCommand(
  command: string[],
  env: NodeJS.ProcessEnv,
  { timeoutMs = 10_000, maxBytes = 1024 * 1024, captureOutput = true } = {},
): Promise<CommandResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(command[0], command.slice(1), { env, stdio: ["ignore", captureOutput ? "pipe" : "ignore", captureOutput ? "pipe" : "ignore"] })
    const stdout: Buffer[] = []
    const stderr: Buffer[] = []
    let bytes = 0
    let failure: Error | undefined
    const stop = (error: Error) => {
      failure ??= error
      child.kill("SIGKILL")
      child.stdout?.destroy()
      child.stderr?.destroy()
    }
    const timer = setTimeout(() => stop(new Error("command timed out")), timeoutMs)
    const capture = (chunks: Buffer[]) => (chunk: Buffer) => {
      bytes += chunk.length
      if (bytes > maxBytes) stop(new Error("command exceeded output limit"))
      else chunks.push(chunk)
    }
    child.stdout?.on("data", capture(stdout))
    child.stderr?.on("data", capture(stderr))
    child.on("error", error => { failure ??= error })
    child.on("close", code => {
      clearTimeout(timer)
      if (failure) reject(failure)
      else resolve({ exitCode: code ?? -1, stdout: Buffer.concat(stdout).toString(), stderr: Buffer.concat(stderr).toString() })
    })
  })
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function response(result: CommandResult): Record<string, unknown> {
  if (result.exitCode !== 0) throw new Error(`CBM command exited ${result.exitCode}: ${(result.stderr || result.stdout).slice(0, 500)}`)
  const envelope: unknown = JSON.parse(result.stdout)
  if (!object(envelope) || envelope.isError === true) throw new Error("CBM returned an invalid response or MCP error")
  let data = envelope.structuredContent
  if (data === undefined && Array.isArray(envelope.content)) {
    const text = envelope.content.find(entry => object(entry) && entry.type === "text")
    if (object(text) && typeof text.text === "string") data = JSON.parse(text.text)
  }
  if (!object(data)) throw new Error("CBM response has no JSON result")
  return data
}

const inFlight = new Map<string, Promise<void>>()

/** Register one workspace best-effort; callers need not await graph readiness. */
export async function registerWorkspace(
  directory: string,
  config: WorkspaceConfig,
  adapters: Partial<RegistrationAdapters> = {},
): Promise<void> {
  const entry = config.mcp?.["codebase-memory-mcp"]
  if (!object(entry) || entry.type !== "local" || entry.enabled === false || entry.disabled === true ||
      !Array.isArray(entry.command) || entry.command.length === 0 ||
      !entry.command.every(arg => typeof arg === "string" && arg.length > 0)) return
  const command = [...entry.command] as string[]
  const env = { ...process.env, ...(object(entry.environment) ? entry.environment : {}) } as NodeJS.ProcessEnv
  const run = adapters.run ?? runCommand
  try {
    const git = await run(["git", "-C", directory, "rev-parse", "--show-toplevel"], process.env)
    if (git.exitCode !== 0) return
    const root = await realpath(git.stdout.trim())
    const existing = inFlight.get(root)
    if (existing) return await existing
    const attempt = (async () => {
      let offset = 0
      for (;;) {
        const args = ["cli", "--json", "list_projects", "--format", "json"]
        if (offset) args.push("--offset", String(offset))
        const data = response(await run([...command, ...args], env))
        if (!Array.isArray(data.projects) || typeof data.has_more !== "boolean") throw new Error("CBM returned an invalid project page")
        for (const project of data.projects) {
          if (!object(project) || typeof project.root_path !== "string") throw new Error("CBM returned an invalid project root")
          // Indexed roots can outlive their checkout; canonicalize those still present.
          const canonical = await realpath(project.root_path).catch(() => project.root_path)
          if (canonical === root) return
        }
        if (!data.has_more) break
        if (!Number.isSafeInteger(data.next_offset) || (data.next_offset as number) <= offset) throw new Error("CBM returned invalid pagination")
        offset = data.next_offset as number
      }
      // A detached daemon can inherit startup pipes and keep them open indefinitely.
      const daemon = await run([...command, "daemon", "start"], env, { captureOutput: false })
      if (daemon.exitCode !== 0) throw new Error(`CBM daemon start failed: ${daemon.stderr.slice(0, 500)}`)
      response(await run([...command, "cli", "--json", "index_repository", "--repo-path", root, "--async", "true"], env))
    })()
    inFlight.set(root, attempt)
    try { await attempt } finally { if (inFlight.get(root) === attempt) inFlight.delete(root) }
  } catch (error) {
    try {
      await adapters.log?.(`CBM workspace registration failed: ${error instanceof Error ? error.message : String(error)}`)
    } catch {
      // Diagnostics must not turn a best-effort registration into a config failure.
    }
  }
}
