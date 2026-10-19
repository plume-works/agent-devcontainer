import { afterAll, describe, expect, test } from "bun:test"
import { mkdirSync, mkdtempSync, realpathSync, rmSync, symlinkSync } from "node:fs"
import path from "node:path"
import { registerWorkspace, runCommand } from "../../.opencode-plugin/workspace-index.ts"

const scratch = path.resolve(import.meta.dir, "../../../../../.tmp")
mkdirSync(scratch, { recursive: true })
const fixture = mkdtempSync(path.join(scratch, "workspace-index-"))
afterAll(() => rmSync(fixture, { recursive: true, force: true }))

function git(...args: string[]) {
  const result = Bun.spawnSync(["git", ...args])
  if (result.exitCode) throw new Error(result.stderr.toString())
}

function repository(name: string) {
  const root = path.join(fixture, name)
  git("init", root)
  return realpathSync(root)
}

const root = repository("other repository")
const subdir = path.join(root, "nested")
mkdirSync(subdir)
const alias = path.join(fixture, "alias")
symlinkSync(root, alias)
git("-C", root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "--allow-empty", "-m", "initial")
const worktree = path.join(fixture, "worktree")
git("-C", root, "worktree", "add", "-b", "fixture-worktree", worktree)

const config = { mcp: { "codebase-memory-mcp": {
  type: "local", command: ["configured-cbm", "--prefix"],
  environment: { CBM_CACHE_DIR: "/fixture/cache", CBM_ALLOWED_ROOT: fixture },
} } }
const ok = (data: unknown) => ({ exitCode: 0, stdout: JSON.stringify({ structuredContent: data, isError: false }), stderr: "" })
const page = (roots: string[] = [], extra = {}) => ok({ projects: roots.map(root_path => ({ root_path })), has_more: false, ...extra })

function harness(responses = [page(), { exitCode: 0, stdout: "daemon started", stderr: "" }, ok({ state: "running" })]) {
  const calls: { command: string[]; env: NodeJS.ProcessEnv }[] = []
  const logs: string[] = []
  return {
    calls, logs,
    adapters: {
      run: async (command: string[], env: NodeJS.ProcessEnv) => {
        if (command[0] === "git") return runCommand(command, { ...env, GIT_CEILING_DIRECTORIES: fixture })
        calls.push({ command, env })
        const response = responses.shift()
        if (!response) throw new Error("unexpected command")
        return response
      },
      log: async (message: string) => { logs.push(message) },
    },
  }
}

describe("workspace registration", () => {
  for (const directory of [root, subdir, alias, worktree]) {
    test(`registers the canonical worktree from ${path.basename(directory)}`, async () => {
      const h = harness()
      await registerWorkspace(directory, config, h.adapters)
      const expected = directory === worktree ? realpathSync(worktree) : root
      expect(h.calls.map(c => c.command)).toEqual([
        ["configured-cbm", "--prefix", "cli", "--json", "list_projects", "--format", "json"],
        ["configured-cbm", "--prefix", "daemon", "start"],
        ["configured-cbm", "--prefix", "cli", "--json", "index_repository", "--repo-path", expected, "--async", "true"],
      ])
      expect(h.calls[0].env.CBM_CACHE_DIR).toBe("/fixture/cache")
      expect(h.calls[0].env.CBM_ALLOWED_ROOT).toBe(fixture)
      expect(h.calls[0].env.PATH).toBe(process.env.PATH)
      expect(h.logs).toEqual([])
    })
  }

  test("skips a registered canonical root, including a symlinked project path", async () => {
    const h = harness([page([alias])])
    await registerWorkspace(subdir, config, h.adapters)
    expect(h.calls).toHaveLength(1)
  })

  test("uses exact roots and follows project pagination", async () => {
    const h = harness([page([path.dirname(root)], { has_more: true, next_offset: 50 }), page([root])])
    await registerWorkspace(root, config, h.adapters)
    expect(h.calls).toHaveLength(2)
    expect(h.calls[1].command.slice(-2)).toEqual(["--offset", "50"])
  })

  test("an ancestor project does not count as registration", async () => {
    const h = harness([page([fixture]), { exitCode: 0, stdout: "", stderr: "" }, ok({ state: "running" })])
    await registerWorkspace(root, config, h.adapters)
    expect(h.calls).toHaveLength(3)
  })

  test("accepts the MCP text-content JSON envelope", async () => {
    const h = harness([{ exitCode: 0, stderr: "", stdout: JSON.stringify({ content: [{ type: "text", text: JSON.stringify({ projects: [{ root_path: root }], has_more: false }) }] }) }])
    await registerWorkspace(root, config, h.adapters)
    expect(h.calls).toHaveLength(1)
    expect(h.logs).toEqual([])
  })

  test("quietly skips absent, disabled, remote, and commandless MCP config", async () => {
    for (const entry of [undefined, { enabled: false }, { type: "remote", url: "https://example.test" }, { type: "local", command: [] }]) {
      const h = harness()
      await registerWorkspace(root, { mcp: { "codebase-memory-mcp": entry } }, h.adapters)
      expect(h.calls).toEqual([])
      expect(h.logs).toEqual([])
    }
  })

  test("quietly skips a local entry that v1 or v2 config disables", async () => {
    const entry = config.mcp["codebase-memory-mcp"]
    for (const disabled of [{ ...entry, enabled: false }, { ...entry, disabled: true }]) {
      const h = harness()
      await registerWorkspace(root, { mcp: { "codebase-memory-mcp": disabled } }, h.adapters)
      expect(h.calls).toEqual([])
      expect(h.logs).toEqual([])
    }
  })

  test("registers a v2 local entry that is not disabled", async () => {
    const h = harness()
    await registerWorkspace(root, { mcp: { "codebase-memory-mcp": { ...config.mcp["codebase-memory-mcp"], disabled: false } } }, h.adapters)
    expect(h.calls).toHaveLength(3)
  })

  test("quietly skips a non-Git directory", async () => {
    const nonGit = path.join(fixture, "non-git")
    mkdirSync(nonGit)
    const h = harness()
    await registerWorkspace(nonGit, config, h.adapters)
    expect(h.calls).toEqual([])
    expect(h.logs).toEqual([])
  })

  test("shares overlapping attempts but treats separate worktrees independently", async () => {
    const calls: string[][] = []
    let release!: () => void
    const pending = new Promise<void>(resolve => { release = resolve })
    const adapters = { log: async () => {}, run: async (command: string[], env: NodeJS.ProcessEnv) => {
      if (command[0] === "git") return runCommand(command, env)
      calls.push(command)
      await pending
      return page([root, worktree])
    } }
    const attempts = [registerWorkspace(root, config, adapters), registerWorkspace(alias, config, adapters), registerWorkspace(worktree, config, adapters)]
    await Bun.sleep(100)
    expect(calls).toHaveLength(2)
    release()
    await Promise.all(attempts)
  })

  for (const [name, response] of [
    ["malformed JSON", { exitCode: 0, stdout: "not-json", stderr: "" }],
    ["MCP error", { exitCode: 0, stdout: JSON.stringify({ isError: true, structuredContent: {} }), stderr: "" }],
    ["denied root", { exitCode: 1, stdout: "", stderr: "root denied" }],
    ["invalid projects", ok({ projects: null, has_more: false })],
    ["invalid pagination", page([], { has_more: true, next_offset: 0 })],
  ] as const) {
    test(`logs ${name} and never submits after a failed lookup`, async () => {
      const h = harness([response])
      await registerWorkspace(root, config, h.adapters)
      expect(h.calls).toHaveLength(1)
      expect(h.logs).toHaveLength(1)
      expect(h.logs[0]).toContain("CBM workspace registration")
    })
  }

  test("spawn failures and logging failures do not reject; next initialization retries", async () => {
    await registerWorkspace(root, config, {
      run: async (command, env) => {
        if (command[0] === "git") return runCommand(command, env)
        throw new Error("spawn failure")
      },
      log: async () => { throw new Error("logging unavailable") },
    })
    const h = harness()
    await registerWorkspace(root, config, h.adapters)
    expect(h.calls).toHaveLength(3)
  })

  test("logs a rejected index submission", async () => {
    const h = harness([page(), { exitCode: 0, stdout: "", stderr: "" }, { exitCode: 0, stdout: JSON.stringify({ isError: true }), stderr: "" }])
    await registerWorkspace(root, config, h.adapters)
    expect(h.logs).toHaveLength(1)
  })

  for (const [name, script] of [
    ["timed out", "setInterval(() => {}, 1000)"],
    ["output limit", 'process.stdout.write("x".repeat(1024 * 1024 + 1)); setInterval(() => {}, 1000)'],
  ]) {
    test(`logs ${name} without submitting an index`, async () => {
      const logs: string[] = []
      let calls = 0
      await registerWorkspace(root, config, {
        run: async (command, env) => {
          if (command[0] === "git") return runCommand(command, env)
          calls++
          return runCommand([process.execPath, "-e", script], env, { timeoutMs: 500 })
        },
        log: async message => { logs.push(message) },
      })
      expect(calls).toBe(1)
      expect(logs[0]).toContain(name)
    })
  }
})

describe("bounded subprocess adapter", () => {
  test("daemon startup does not wait for a detached daemon's inherited pipes", async () => {
    const start = Date.now()
    const result = await runCommand([process.execPath, "-e", 'const child = require("node:child_process").spawn(process.execPath, ["-e", "setTimeout(() => {}, 1000)"], { detached: true, stdio: "inherit" }); child.unref()'], process.env, { captureOutput: false })
    expect(result.exitCode).toBe(0)
    expect(Date.now() - start).toBeLessThan(800)
  })

  test("timeout also closes pipes inherited by a child of an exited process", async () => {
    await expect(runCommand([process.execPath, "-e", 'const child = require("node:child_process").spawn(process.execPath, ["-e", "setTimeout(() => {}, 1000)"], { detached: true, stdio: "inherit" }); child.unref()'], process.env, { timeoutMs: 100 })).rejects.toThrow("timed out")
  })

  test("reports an unavailable executable", async () => {
    await expect(runCommand(["/no/such/cbm"], process.env)).rejects.toThrow()
  })

  test("terminates a timed-out child even when it ignores SIGTERM", async () => {
    const started = Date.now()
    await expect(runCommand([process.execPath, "-e", 'process.on("SIGTERM", () => {}); setInterval(() => {}, 1000)'], process.env, { timeoutMs: 100 })).rejects.toThrow("timed out")
    expect(Date.now() - started).toBeLessThan(2000)
  })

  for (const stream of ["stdout", "stderr"]) {
    test(`terminates a child exceeding the ${stream} output limit`, async () => {
      await expect(runCommand([process.execPath, "-e", `process.${stream}.write("x".repeat(1024 * 1024 + 1)); setInterval(() => {}, 1000)`], process.env)).rejects.toThrow("output limit")
    })
  }
})
