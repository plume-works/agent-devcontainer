# pr-review replay corpus

Offline replays of the `agentdev:pr-review` skill on real pull requests from
`plume-works/images`, with known defects to find. The analysis is in
[What pr-review variants find on replayed pull requests](../../knowledge/data/findings/pr-review-replay-variants.md);
every run's scored detail is in [results.md](results.md).

## Layout

| Path                         | Holds                                                                                                                                                                                          |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cases/<case>/case.json`     | Source repository, PR number, `base` and `head` commits, which description the case uses, earlier threads, and the `expected` findings with the pattern that scores each one                   |
| `cases/<case>/pr.json`       | Title, body and branches the review reads                                                                                                                                                      |
| `cases/<case>/pr.diff`       | `git diff <base> <head>` in the source repository, what `gh pr diff` prints                                                                                                                    |
| `cases/<case>/files.txt`     | The changed files                                                                                                                                                                              |
| `cases/<case>/threads.json`  | Earlier review threads as GraphQL `reviewThreads` nodes                                                                                                                                        |
| `cases/<case>/comments.json` | The same earlier comments as the REST pull request comments endpoint lists them                                                                                                                |
| `variants.json`              | Each skill variant: the commit it was archived from, its base on `main`, the branch, and the change                                                                                            |
| `variants/<id>.diff`         | The full diff of `.agents/plugins/agentdev` from the variant's base to its commit                                                                                                              |
| `rounds.json`                | Each round: the question, the variants compared, the cases                                                                                                                                     |
| `runs/<variant>/<run>.json`  | One replay: orchestrator model, cost, time, every subagent (role, model requested, model it ran, its final output), every candidate with the validator's verdict, and the review it would post |
| `results.md`                 | Generated: per round, per case, per run, each expected finding scored, every posted comment and dropped candidate                                                                              |
| `tools/run.sh`               | Replays one review                                                                                                                                                                             |
| `tools/cr-prompt.txt`        | The prompt the `cr` baseline runs used                                                                                                                                                         |
| `tools/extract.py`           | Turns a replay's raw output into a run record                                                                                                                                                  |
| `tools/report.py`            | Scores the run records and writes `results.md`                                                                                                                                                 |

A run is named `<case>-<variant>-<n>`. Variant `cr` is Anthropic's
`code-review` plugin 1.0.1, run as an outside baseline. It writes
`{"issues": [...]}` in place of a review, and its candidates name an `agent`
in place of a `pass`.

## Scoring

`tools/report.py` scores each expected finding in each run as one of:

- `posted (<label>)`: a posted comment matches the finding's `match` pattern
  (and its `path_include` file); the label is the severity marker the comment
  opens with.
- `dropped`: no comment matches, but a candidate a pass raised matches and the
  validator dropped it.
- `not raised`: neither.
- `stopped` / `not stopped`, for a `gate-stop` expectation: whether the review
  ended without dispatching any review pass.

An `expect: not-posted` finding is a false finding the review must not raise.

## Replaying a case

1. Clone `plume-works/images` and check out the case's `head` commit.
2. Build the variant's plugin: `git archive <commit> .agents/plugins/agentdev`
   from this repository, extracted so that `<dir>/agentdev` is the plugin root.
3. Run `tools/run.sh <checkout> cases/<case> <dir>/agentdev <run-dir>`. The
   review runs on `claude -p --model opus` with `gh` replaced by a stub that
   fails, and writes `out/review.json` and `out/candidates.json` instead of
   posting.
4. Run `uv run python tools/extract.py <run-dir> ~/.claude/projects runs/<variant>/<run>.json`,
   then `uv run python tools/report.py .` from this directory.

The `cr` runs did not come from `tools/run.sh`. Their prompt, with the run
directory and PR number as placeholders, is in `tools/cr-prompt.txt`; their
sessions loaded `code-review` 1.0.1 with `--plugin-dir` and also this
repository's `agentdev` plugin. The tool permissions they ran with are not
recorded, so a `cr` replay reruns the prompt, not the exact session.

## Measuring a change

- Replay only the stage the change touches. A change to the correctness passes
  is measured on the correctness passes' candidates before validation; a change
  to the validator, on a fixed candidate set. Replaying the whole review adds the
  run-to-run variation of every other stage to the one under test.
- Compare arms on the same `main` base, in the same round.
- Fix the expected findings in `case.json` before the runs.
- Pin the effort level and record it.
- Run enough replays per arm and case that a difference is larger than the
  spread between runs of the same arm; three runs is not enough.
