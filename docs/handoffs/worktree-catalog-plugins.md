# Handoff: per-worktree agentdev catalog (exploration in progress)

Temporary. This file tracks the worktree-catalog thread so its findings and
decisions show up as diffs. It is deleted when `/agentdev:iwe-plan` takes the
thread into a plan, which records its own architecture on completion. How to
write the hooks themselves lives in
`docs/knowledge/data/architecture/worktree-hooks.md`.

## Problem

The catalog is one directory marketplace, `agent-devcontainer`, registered at
the main checkout `/workspaces/agent-devcontainer`. Every session, worktree
sessions included, loads `agentdev` and `self-improve` from there. A stale main
checkout therefore serves stale skills everywhere: the one-question-at-a-time
Explore rules (commit `2553f18a`) never reached worktree sessions while the main
checkout sat 31 commits behind `origin/main`.

## Decided

- Each worktree gets its own catalog through `WorktreeCreate` and
  `WorktreeRemove` hooks configured in user settings (`~/.claude/settings.json`).
- The marketplace name comes from a generated folder
  `~/.claude/wt-marketplaces/wt-<name>/` holding a renamed copy of
  `.claude-plugin/marketplace.json` and a copy of `.agents/plugins/`.
- The shared catalog's `enabledPlugins` move from the main checkout's
  `.claude/settings.local.json` to user settings.
- A worktree's `.claude/settings.local.json` also gets `Bash(*)` and the
  per-worktree plugin-cache permission
  `Bash(/root/.claude/plugins/cache/wt-<name>/agentdev/*)`.
- Remote Control's automatic cleanup of a spawned session's worktree runs
  `WorktreeRemove` (human:author).
- Inline plugins (`--plugin-dir`, `CLAUDE_CODE_PLUGIN_DIRS`) are not the route
  for Remote Control spawns: no hook can turn them on per worktree. They stay a
  manual option for a local session started with `claude -w` (human:author).

## Findings (Claude Code 2.1.316, agent-dev3)

- The marketplace name is the `name` field of the folder's
  `.claude-plugin/marketplace.json`. The `extraKnownMarketplaces` key is ignored
  for a directory source; declaring a worktree path under a new key re-points
  the existing `agent-devcontainer` entry for every session on the machine.
- `claude plugin marketplace add` has no option to set a name.
- `~/.claude/plugins/known_marketplaces.json` is per user: one entry per name.
  `installed_plugins.json` records installs per project path.
- An install refuses a marketplace entry that is absolute, climbs out of the
  marketplace folder, or traverses a symlink, so the generated folder holds real
  copies.
- `WorktreeCreate` replaces worktree creation. stdin carries `session_id`,
  `transcript_path`, `cwd`, `hook_event_name`, `name` (Remote Control spawns also
  send `scratchpad_dir`). The hook prints the worktree's absolute path on stdout;
  success with no path fails the creation.
- `claude remote-control --spawn worktree` creates worktrees through the hook. A
  session spawned from claude.ai started in the hook's folder on branch
  `worktree-bridge-cse_<id>` and loaded `agentdev:iwe-capture` from
  `~/.claude/wt-marketplaces/wt-bridge-cse_<id>/`.
- Archiving a Remote Control session does not run `WorktreeRemove`; Remote
  Control's automatic cleanup does.
- A worktree session reads the main checkout's `.claude/settings.local.json` as
  well as its own, and an `enabledPlugins` value in the main checkout's file wins
  over the worktree's. The worktree's local settings do override user settings.
- With the shared catalog enabled in user settings and disabled in the worktree's
  local settings, a worktree session loads only its `wt-<name>` copy (no
  duplicate agent names), and a main-checkout session still loads from
  `/workspaces/agent-devcontainer`.
- The `SessionStart` hook runs after plugins load, so a reinstall there applies
  from the next session. `SubagentStart` fires on subagent dispatch, not on
  worktree creation.

### A renamed manifest pointing into the worktree (this container)

A copied `.claude-plugin/marketplace.json` with only `name` changed, kept
outside the worktree, cannot point its plugins back at the worktree's
`.agents/plugins/`:

- A string `source` must start with `./`. `./` followed by a path that climbs
  out of the marketplace folder is refused, like an absolute or symlinked entry.
- Object sources `directory` and `local` are refused as unsupported source types.
- A `git-subdir` source with `url: file://<worktree>`, `path:
.agents/plugins/agentdev`, and `ref: <worktree branch>` installs. It clones the
  branch's committed tree into `~/.claude/plugins/cache/<marketplace>/`, so the
  session sees the last commit, not the working tree, and a new commit needs
  `claude plugin update` to show up.

### A file-source marketplace inside the worktree (this container)

- A marketplace can be a single JSON file:
  `claude plugin marketplace add <path>.json` registers it with source
  `{"source": "file", "path": "<path>.json"}`. Its root, against which `./`
  plugin entries resolve, is the parent of the folder holding the file. A file
  at `<worktree>/.claude/marketplace.local.json` therefore has the worktree as
  its root, and the unchanged entry `./.agents/plugins/agentdev` resolves to the
  worktree's own plugin folder.
- `.claude/.gitignore` already ignores `*.local.json`, so that file leaves the
  worktree clean.
- Installed with `--scope local`, the plugin is read in place: `claude plugin
list` shows `Read from: <worktree>/.agents/plugins/agentdev`, and a session's
  `init` event lists a skill that exists only uncommitted in the worktree. No
  copy, no cache, no refresh.
- `claude plugin marketplace add` declares the marketplace in user settings
  (`~/.claude/settings.json` `extraKnownMarketplaces`), one entry per worktree,
  which `WorktreeRemove` must take out again.
- A `file` marketplace declared only in a repository's
  `.claude/settings.local.json` `extraKnownMarketplaces` was not registered in a
  clone under `/tmp`; the hook registers it with the CLI instead.

### Inline plugins: `--plugin-dir` and `CLAUDE_CODE_PLUGIN_DIRS` (this container)

- `claude --plugin-dir <path>` loads a plugin folder for that session only, read
  live from the folder: no copy, no marketplace, no install record.
- The environment variable `CLAUDE_CODE_PLUGIN_DIRS` does the same: a list of
  plugin folders separated by `:`. Each entry must be an absolute path; a
  relative path or one starting with `~` is skipped with a warning.
- An inline plugin replaces an installed plugin of the same name. With
  `agentdev@agent-devcontainer` installed and enabled, a session started with the
  worktree's folder inline lists one `agentdev`, source `agentdev@inline`, with
  the worktree's skills; `self-improve` still comes from the installed catalog.
- The variable takes effect from the shell environment and from the `env` block
  of a `--settings` file. It does not take effect from the `env` block of the
  worktree's `.claude/settings.json` or `.claude/settings.local.json`: the
  session still loads the installed `agentdev`. A `WorktreeCreate` hook therefore
  cannot switch a session to inline plugins by writing project settings.
- `claude plugin list` does not show inline plugins; the `init` event of
  `--output-format stream-json --verbose` does, under `plugins`.
- `claude remote-control --help` lists no `--plugin-dir`. Whether a variable set
  on the Remote Control process reaches the sessions it spawns is untested; it
  would name the same folders for every spawned session.

## Hook scripts as tested

Installed on agent-dev3 at `/root/.claude/wt-hooks/`. Spike quality: no tests,
`/root` paths hard-coded.

`worktree-create.py`:

```python
#!/usr/bin/env python3
"""Spike WorktreeCreate hook: create the worktree and give it its own catalog marketplace."""
import json, os, re, shutil, subprocess, sys, datetime
from pathlib import Path

payload = json.load(sys.stdin)
log = Path.home() / '.claude' / 'wt-hook.log'
with log.open('a') as f:
    f.write(f'{datetime.datetime.now().isoformat()} create {json.dumps(payload)}\n')
repo = Path(payload['cwd']).resolve()
top = Path(subprocess.check_output(['git', '-C', str(repo), 'rev-parse', '--show-toplevel'], text=True).strip())
name = re.sub(r'[^A-Za-z0-9._-]', '-', payload['name'])
wt = top / '.claude' / 'worktrees' / name
subprocess.run(['git', '-C', str(top), 'worktree', 'add', '-q', '-b', f'worktree-{name}', str(wt), 'HEAD'],
               check=True, stdout=sys.stderr)
market = f'wt-{name}'
mdir = Path.home() / '.claude' / 'wt-marketplaces' / market
shutil.rmtree(mdir, ignore_errors=True)
(mdir / '.claude-plugin').mkdir(parents=True)
manifest = json.loads((wt / '.claude-plugin' / 'marketplace.json').read_text())
manifest['name'] = market
(mdir / '.claude-plugin' / 'marketplace.json').write_text(json.dumps(manifest, indent=2))
shutil.copytree(wt / '.agents' / 'plugins', mdir / '.agents' / 'plugins', symlinks=False)
src = top / '.claude' / 'settings.local.json'
settings = json.loads(src.read_text()) if src.exists() else {}
plugins = [p['name'] for p in manifest['plugins']]
enabled = {k: v for k, v in settings.get('enabledPlugins', {}).items() if not k.endswith('@agent-devcontainer')}
enabled.update({f'{p}@agent-devcontainer': False for p in plugins})
enabled.update({f'{p}@{market}': True for p in plugins})
settings['enabledPlugins'] = enabled
settings['extraKnownMarketplaces'] = {market: {'source': {'source': 'directory', 'path': str(mdir)}}}
allow = settings.setdefault('permissions', {}).setdefault('allow', [])
for rule in ('Bash(*)', f'Bash(/root/.claude/plugins/cache/{market}/agentdev/*)'):
    if rule not in allow:
        allow.append(rule)
(wt / '.claude').mkdir(exist_ok=True)
(wt / '.claude' / 'settings.local.json').write_text(json.dumps(settings, indent=2) + '\n')
print(wt)
```

`worktree-remove.py` (reads `worktree_path`; the field name Remote Control's
cleanup sends is not yet confirmed):

```python
#!/usr/bin/env python3
"""Spike WorktreeRemove hook: drop the worktree's marketplace, then the worktree."""
import json, subprocess, sys, shutil, datetime
from pathlib import Path

payload = json.load(sys.stdin)
with (Path.home() / '.claude' / 'wt-hook.log').open('a') as f:
    f.write(f'{datetime.datetime.now().isoformat()} remove {json.dumps(payload)}\n')
wt = Path(payload.get('worktree_path') or payload.get('worktreePath') or payload.get('path'))
market = f'wt-{wt.name}'
subprocess.run(['claude', 'plugin', 'marketplace', 'remove', market], cwd=str(wt) if wt.exists() else None,
               stdout=sys.stderr, stderr=sys.stderr, check=False)
shutil.rmtree(Path.home() / '.claude' / 'wt-marketplaces' / market, ignore_errors=True)
if wt.exists():
    subprocess.run(['git', '-C', str(wt), 'worktree', 'remove', '--force', str(wt)], stdout=sys.stderr, check=False)
```

User settings entries:

```json
"hooks": {
  "WorktreeCreate": [{"hooks": [{"type": "command", "command": "/root/.claude/wt-hooks/worktree-create.py"}]}],
  "WorktreeRemove": [{"hooks": [{"type": "command", "command": "/root/.claude/wt-hooks/worktree-remove.py"}]}]
},
"enabledPlugins": {
  "agentdev@agent-devcontainer": true,
  "self-improve@agent-devcontainer": true
}
```

## State left on agent-dev3

- Both hooks are configured in `/root/.claude/settings.json`, and Remote Control
  runs with them (tmux socket `claude-remote`).
- `enabledPlugins` moved from `/workspaces/agent-devcontainer/.claude/settings.local.json`
  into `/root/.claude/settings.json`.
- Backups: `/root/.claude/settings.json.bak-wt-spike`,
  `/workspaces/agent-devcontainer/.claude/settings.local.json.bak-wt-spike`.
- Test worktrees, branches, marketplaces, and install records are removed.

## Open

- Keep the agent-dev3 setup live, or restore the backups and restart Remote
  Control.
- Which field `WorktreeRemove` receives from Remote Control's cleanup.
- A worktree's copied catalog does not follow catalog edits made in the
  worktree; whether a refresh is needed, and when.
- Where the hooks and the settings move live in the repository: the
  `agentic_tools` Ansible role, `agentdev-runtime`, or the catalog.
- Which container startup step writes `Bash(*)` today, so the hook and it stay
  one source.
- The main checkout on this machine is 31 commits behind `origin/main`;
  fast-forwarding it is still pending.
