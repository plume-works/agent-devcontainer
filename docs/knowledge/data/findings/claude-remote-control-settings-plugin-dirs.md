---
type: finding
description: A Remote Control server that starts with --settings gives each session that it spawns the plugins of one folder through CLAUDE_CODE_PLUGIN_DIRS. A copy of the plugin in the worktree of a session has no effect. The maintainer has not made a decision to use this method.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/worktree.py
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/settings
- resource: https://code.claude.com/docs/en/env-vars
---

# Claude Remote Control settings file and plugin folders

This finding refers to [Each worktree loads its catalog from a marketplace in
the worktree](../adr/0057-worktree-catalog-from-in-worktree-marketplace.md). The
measurement used Claude Code 2.1.325. The question: can all sessions of a Remote
Control server load the catalog from one checkout, as an alternative to a
catalog for each worktree?

## Measurement

The per-worktree catalog of ADR-0057, in a worktree session of this repository:

- **The session reads the catalog from its worktree.** `claude plugin list`
  shows the worktree folder as the source. The plugin cache holds a copy of the
  catalog that the session does not read.
- **`/reload-skills` uses the content of the worktree.** It adds a skill that is
  new in the worktree and removes a skill that is deleted there. The session
  does not restart.
- **A checkout changes the skill bodies.** After a checkout of a different
  branch in the worktree, the session loads the skill bodies of that branch.
- **A change in the main checkout has no effect.** The worktree session does not
  show a skill that is only in the main checkout.

`CLAUDE_CODE_PLUGIN_DIRS`, the variable that loads a folder of plugins the way
`--plugin-dir` does:

- **The variable has an effect in the process environment.** `claude -p` in a
  worktree, with the variable set to the `.agents/plugins` folder of a different
  checkout, loads the plugins of that folder.
- **The variable has an effect in a `--settings` file.**
  `claude --settings <file>` loads the plugins when the `env` block of the file
  sets the variable. The documentation puts `--settings` above the user,
  project, and local settings files.
- **`claude remote-control` has no `--plugin-dir`.** The help text and the
  documentation list none. The documentation says that a global flag before
  `remote-control` does not go to the sessions.

A Remote Control server in a separate container, started with
`claude remote-control --spawn worktree --settings <file>`, where the `env`
block of the file sets `CLAUDE_CODE_PLUGIN_DIRS` to an absolute folder outside
the repository:

- **Each spawned session gets the settings file.** The process of the
  pre-created session, which the server creates in its own folder when it
  starts, has `--settings=<file>` on the command line and the variable in the
  environment. The process of a worktree session has the same two items.
- **Each spawned session has the plugin.** A user ran the skill of the plugin in
  the pre-created session and in a worktree session.
- **A change in the folder goes to the sessions that are in operation.** After a
  change to the skill body in the folder and `/reload-skills`, both sessions ran
  the changed skill. The test does not show if the reload was necessary.
- **A copy in the worktree has no effect.** With a different copy of the plugin
  in the worktree of the session, the session ran the skill of the folder,
  before and after `/reload-skills`.
- **The plugin of the folder replaces an installed plugin of the same name.**
  The same plugin was also installed at user scope from a marketplace and
  enabled. `claude plugin list` shows the two plugins. The session has one
  skill, the skill of the folder. Without the settings file, the session has the
  skill of the installed plugin.
- **A changed description needs `/reload-skills`.** The test used a `claude -p`
  session with more than one turn and the plugin of the folder. The skill list
  of the session does not show a change to the `description` in the frontmatter
  of a skill. After `/reload-skills`, the session has the changed description,
  and the reload reports no added or removed skill.

## Eliminated hypotheses

- **"A worktree session reads a copy of the catalog."** Eliminated: the session
  loaded a skill that was not committed in its worktree.
- **"A worktree session can only run the catalog of the base branch."**
  Eliminated: a checkout of a different branch in the worktree changed the skill
  bodies that the session loaded.
- **"No setting can give the variable to the sessions of a Remote Control
  server."** Eliminated: the `--settings` flag of `claude remote-control` does.
  The limit that ADR-0057 records applies to the settings files of a worktree.

## Consequences

- With one folder for all sessions, a session that changes the catalog in its
  worktree cannot run the change. The per-worktree catalog has the opposite
  property: only the worktree of the session has an effect.
- A session with the per-worktree catalog can run the catalog of any branch: do
  a checkout of the branch in the worktree of the session.

## Closing

Open. The maintainer decides between the per-worktree catalog of ADR-0057 and
one folder for all sessions. A decision for one folder is a new ADR that
supersedes ADR-0057. A decision to keep ADR-0057 closes this finding with no
change.
