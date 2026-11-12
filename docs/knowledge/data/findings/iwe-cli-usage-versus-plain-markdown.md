---
type: finding
description: What agent sessions use the iwe CLI for, measured over two weeks of Claude Code transcripts — mostly formatting and schema validation, rarely retrieval or reference rewriting — and what that means for keeping it over plain Markdown files.
sources:
- resource: .iwe/config.toml
- resource: .pre-commit-config.yaml
- resource: .github/workflows/validate-knowledge-base.yml
- resource: docs/knowledge/AGENTS.md
- id: iwe-repo
  resource: https://github.com/iwe-org/iwe
- id: iwe-releases
  resource: https://github.com/iwe-org/iwe/releases
- id: iwe-show-hn
  resource: https://news.ycombinator.com/item?id=46662307
- id: iwe-agent-blog
  resource: https://iwe.md/blog/your-agent-hates-walking-your-knowledge-graph/
- id: iwe-benchmark
  resource: https://iwe.md/blog/benchmarking-iwe-on-20000-documents/
- id: letta
  resource: https://www.letta.com/blog/benchmarking-ai-agent-memory
- id: agents-md-study
  resource: https://arxiv.org/pdf/2602.11988
usage_window:
  from: 2026-10-29
  to: 2026-11-10
---

# iwe CLI usage versus plain Markdown

## Question

Does the `iwe` CLI earn its place as the tool that manages `docs/knowledge/`, or
would plain Markdown files read and edited with ordinary tools serve agent
sessions as well?

## Measurement

Claude Code transcripts stored on one Dev Container host, 2026-10-29 to
2026-11-10: 310 session files, subagent transcripts included, with end-to-end
test sessions and scratch-directory sessions left out. Sessions that ran on
other hosts are not in the sample. `iwe` was at 0.29.1 and then 0.32.0. Each
Bash tool call was matched against the `iwe` subcommands, and each read of
`docs/knowledge` through `grep`, `cat`, `sed`, `Read`, or `Grep` was counted as
a plain read.

| Measure                                                                   | Count  |
| ------------------------------------------------------------------------- | ------ |
| All tool calls                                                            | 11,882 |
| Plain reads of `docs/knowledge`                                           | 3,848  |
| Bash calls that run `iwe`                                                 | 1,363  |
| Calls running only `iwe normalize`, `iwe schema validate`, or `iwe stats` | 1,049  |
| Calls reading the graph (`iwe find`, `iwe retrieve`, `iwe tree`)          | 197    |
| Calls writing (`iwe new`, `iwe update`, `iwe delete`, `iwe rename`)       | 127    |

The 197 read calls held 171 executed reads; the rest only quoted a command in
text being edited. Each executed read was labelled by what one `grep` or `cat`
could have answered:

| Kind of read                                                          | Calls | One `grep` or `cat` suffices | Needs a multi-step script |
| --------------------------------------------------------------------- | ----- | ---------------------------- | ------------------------- |
| `iwe find --filter` on frontmatter                                    | 74    | 38                           | 36                        |
| `iwe find --fuzzy` or `--lexical`                                     | 66    | 66                           | 0                         |
| `iwe find` by link (`--references`, `--includes`, and their inverses) | 17    | 15                           | 2                         |
| `iwe retrieve`                                                        | 8     | 8                            | 0                         |
| Help, version, and other                                              | 6     | —                            | —                         |

In 114 of the 171, the same Bash command also read `docs/knowledge` with a plain
tool.

Write calls:

- `iwe rename` ran 3 times and rewrote links in 2, 7, and 2 other documents.
- `iwe delete` rewrote links in other documents in 4 observed runs (1 to 6
  documents each); about a dozen more runs updated none.
- `iwe update` ran 25 times, 23 of them setting one frontmatter field (`stage`,
  `completed`, or `rank`).
- `iwe new` ran in 54 calls, about 22 of which succeeded on the first attempt.
  The recurring failure is an omitted positional title; 21 `--help` lookups
  accompany the write calls.

Validation and failures:

- `iwe schema validate` ran 808 times at about 3.6 seconds a run on 419
  documents. Two runs are confirmed to have caught a document mistake: a `stage`
  value outside the enum and a spec missing `type`. Output piped through `tail`
  hid many results, so two is a lower bound.
- The document-schema language rejected the `if`, `then`, and `anyOf` keywords,
  so a rule conditional on a frontmatter value cannot be expressed in
  `.iwe/schemas/`.
- `iwe` panicked with a broken pipe 9 times when piped into `head`, after
  printing its results. Eight tool results reported `iwe` missing or run outside
  the repository root.

The repository owner's typed messages in the same sessions contain no complaint
about the `iwe` CLI and no statement that it helped. The complaints present are
about the workflow skills and document conventions layered on it: the cost of
the `iwe-verifier` revision round, hub and OKF upkeep, and rules duplicated
between skills.

In the same window 128 of 274 commits touched `docs/knowledge/data`, and 57
touched nothing else.

Outside the repository:

- No independent evaluation of IWE was found. The one third-party-hosted thread
  is its author's own
  announcement.[^iwe-show-hn](https://news.ycombinator.com/item?id=46662307)
- IWE's own material claims fewer serial tool calls from `iwe retrieve` and
  `iwe find`, without token or task-quality
  figures;[^iwe-agent-blog](https://iwe.md/blog/your-agent-hates-walking-your-knowledge-graph/)
  its one benchmark measures parse and query
  speed.[^iwe-benchmark](https://iwe.md/blog/benchmarking-iwe-on-20000-documents/)
- IWE is pre-1.0, published ten releases between 2026-10-08 and
  2026-11-07,[^iwe-releases](https://github.com/iwe-org/iwe/releases) and shows
  one visible maintainer.[^iwe-repo](https://github.com/iwe-org/iwe)
- Published comparisons of agent memory lean towards plain files as a strong
  baseline: Letta reports a filesystem-only agent scoring above a dedicated
  memory tool,[^letta](https://www.letta.com/blog/benchmarking-ai-agent-memory)
  and a study of repository context files reports no significant gain in task
  success at higher cost.[^agents-md-study](https://arxiv.org/pdf/2602.11988)
  Neither measures a project-memory graph, and neither was read past its
  summary.

## What is known

- **Agent sessions treat the knowledge base as plain Markdown.** Plain reads
  outnumber `iwe` reads about twenty to one, and two thirds of the `iwe` reads
  are accompanied by a plain read in the same command.
- **The `iwe` CLI works here as a formatter and a schema validator.** Three
  quarters of its calls are `iwe normalize` and `iwe schema validate`, which the
  pre-commit hooks in `.pre-commit-config.yaml` and
  `.github/workflows/validate-knowledge-base.yml` run anyway.
- **Structured frontmatter queries are the read `iwe` does better than `grep`.**
  They combine several fields or sort by one, as the build-order query in
  `docs/knowledge/AGENTS.md#start-of-every-session` does. They occur about three
  times a day.
- **Reference rewriting is the one capability plain files lack, and it is
  rare:** seven observed uses in two weeks.
- **The cost of project memory is in the process, not the CLI.** The CLI is fast
  and rarely fails; the commit share and the owner's complaints both point at
  the workflow skills and conventions, which a move to plain Markdown would
  leave unchanged.
- **Leaving `iwe` is cheap in data and costly in tooling.** The documents are
  already plain Markdown. The bindings are the fourteen schemas under
  `.iwe/schemas/`, the tests under `docs/knowledge/tests/`, the two pre-commit
  hooks, the validation workflow, and the catalog skills and agents that name
  `iwe` subcommands.

## Eliminated

- **`iwe` is how agents retrieve project memory.** Eliminated by the read
  counts: 171 `iwe` reads against 3,848 plain reads, with `iwe retrieve` used 8
  times.
- **The `iwe` CLI is a source of session failures.** Eliminated: the panics
  print their results first, and missing-binary or wrong-directory results
  number eight.
- **Independent evidence shows IWE improves agent outcomes.** Eliminated: none
  exists, and IWE's own benchmark measures speed only.

## What would settle the rest

- How many document mistakes `iwe schema validate` stops at commit time. The
  transcripts show what agents ran by hand, not what the pre-commit hook or CI
  rejected; the count of failed `validate-knowledge-base` runs and hook
  rejections over the same window answers it.
- Whether the sample is representative: the same count over transcripts from the
  other hosts.

## Closing

The measurement supports two consistent positions, and the choice follows from
whether the schema-enforced workflow stays, which is the repository owner's
decision:

- **The schema-enforced knowledge base stays:** keep `iwe` as its formatter and
  validator, and stop instructing agents to run `iwe normalize` and
  `iwe schema validate` by hand, since the hooks do.
- **The knowledge base becomes plain Markdown or moves to another spec
  workflow:** drop `iwe`. What is lost is about three structured queries a day
  and a handful of reference rewrites, which `grep` and a short script cover.
