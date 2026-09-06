---
type: architecture
description: A colocated per-directory file carrying agent tooling metadata, resolved root-to-leaf with accumulating namespaced sections.
generated:
  by: claude-code/opus-5
  at: 2026-09-06T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py
- resource: docs/knowledge/data/architecture/template-boundary.md
---

# Agent metadata files

## Decision

Agent tooling reads per-directory metadata from `.agent.metadata.json` files
placed anywhere in the source tree. No consumer implements this yet; the rules
below bind the first one that does. Each file is a JSON object whose top-level
keys namespace one consumer apiece:

``` json
{
  "iwe-map": {
    "digest_ignore": {}
  }
}
```

A consumer reads only its own key. A file carrying a key no installed tool
claims is valid and inert, which is what lets a directory declare metadata for
tooling a given checkout does not have.

The format is deliberately general: digest masks for the codebase-map staleness
check are its first consumer, not its purpose.

## Resolution

A consumer resolving metadata for a file walks from the repository root down to
that file's own directory, reading every `.agent.metadata.json` it passes.

``` text
resolving .github/workflows/ci.yml

  /.agent.metadata.json                    ─┐
  /.github/.agent.metadata.json             │ read in this order
  /.github/workflows/.agent.metadata.json  ─┘
```

- **The walk starts at the repository root** — `git rev-parse --show-toplevel`,
  not the invoking directory, so a result never depends on where a tool was run
  from.
- **Sections accumulate**, shallowest first. A deeper file adds to what its
  ancestors declared rather than replacing it, so a subdirectory cannot silently
  lose a repository-wide rule by declaring one of its own. Precedence between
  two rules reaching the same file is the consumer's to define; for ordered
  transformations it is application order, deeper applied last.
- **Globs are relative to the directory holding the file that declares them.** A
  `.github/.agent.metadata.json` matching `**/*.yml` keeps working when
  `.github/` is copied into another repository, which is what makes colocation
  worth its cost. `**` crosses directory separators; a single `*` does not.

Accumulation has no removal operation. If a subtree ever needs to escape an
inherited rule, that is a new key with its own semantics, not a reinterpretation
of this one.

## Failure containment

A `.agent.metadata.json` that cannot be parsed, or whose content a consumer
rejects, marks **its own directory subtree** as unresolvable. A consumer
reporting on that subtree reports it as broken; a consumer reporting on a
subtree the walk never enters is unaffected.

``` text
ansible/roles/perm_probe/.agent.metadata.json  ← malformed
   │
   ├─ ansible/roles/perm_probe   BROKEN   the walk reads it
   ├─ ansible                    BROKEN   its walk descends through it
   └─ .github, .devcontainer     unaffected
```

Containment is by subtree rather than by directory: a consumer asking about an
ancestor reads every descendant file the walk reaches, so a broken file breaks
every scope containing it. The alternative — skipping an unreadable file — makes
a tool silently compute the wrong answer, which for a staleness check means
reporting content as unchanged because the rules that would have flagged it
never loaded.

## Relationship to the template boundary

[Template boundary](template-boundary.md) classifies every tracked path as
Template, Customize, Optional, Publisher, or Generated, and
`/agentdev:template-consume` copies adopted paths on that classification.

A colocated metadata file needs no entry of its own: it inherits the class of
the directory holding it. `.devcontainer/.agent.metadata.json` travels with the
Template-class `.devcontainer/`; a file under `ansible/` stays Publisher and is
never copied. A consuming repository that adopts a directory receives the rules
governing that directory in the same operation, with nothing to reconcile.

## Alternatives considered

**A single repository-level map.** One file — say
`docs/knowledge/digest-masks.json` — binding repository-root-relative globs to
rules. It is simpler to read and needs no walk, and for a small rule set it is
less machinery. It was rejected on ownership: the rules describe directories, so
a central file is edited at a distance by someone who has to know it exists, it
does not travel when a directory is copied, and it needs its own line in the
template-boundary classification. A directory that moves leaves its entry
behind, pointing at a path that no longer exists.

**Replace rather than accumulate**, in the manner of `.gitignore` precedence. It
gives a subtree total control, but the common case is a subtree adding one rule,
and under replacement that silently drops every inherited rule — a failure that
presents as a tool quietly doing less than it did before.

**Repository-root-relative globs in every file.** Uniform and simpler to
implement, but a copied directory's globs then point at its old location, which
removes the portability that motivates colocation.

## Consumers

- `iwe-map` / `digest_ignore` — masks machine-managed content out of the
  codebase-map source fingerprint. Planned in
  [Digest masks for map docs](../plans/20260905-digest-masks.md).

## Key references

Verified anchor points (line numbers as of 2026-09-06):

- `docs/knowledge/data/architecture/template-boundary.md:19-25` — the
  classification a colocated file inherits from its directory
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:123-138` —
  `source_digest_for_paths`, the fingerprint the first consumer filters
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:175-215` —
  `classify`, the per-document verdict function a broken subtree reports through
