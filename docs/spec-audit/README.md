# Spec audit data

Every requirement and every `## Rationale` entry in `docs/knowledge/data/spec/`,
compared with the code, rulebook, or configuration it describes at commit
`c81efa7e`. The comparison is by reading; no test suite was run. The measurement
and what it shows are in
[the finding](../knowledge/data/findings/spec-usefulness-audit.md).

A plan that replaces a spec reads that spec's rows here to learn which
requirements a test already states, which need a test first, which hold a
decision, and which statements are wrong.

## Files

| File                 | One row per                                      | Rows |
| -------------------- | ------------------------------------------------ | ---- |
| `requirements.jsonl` | requirement                                      | 264  |
| `rationale.jsonl`    | `###` entry under `## Rationale`                 | 189  |
| `specs.jsonl`        | spec                                             | 40   |
| `aggregate.py`       | summarises the three files                       |      |
| `source-coupling.py` | counts source commits that also changed the spec |      |

Each row names its spec in `spec`, the file name without `.md`. Places are named
by anchor (`path::symbol`, `path#heading-slug`, `path#key.path`), never by line.

```bash
docs/spec-audit/aggregate.py                      # counts of every field
docs/spec-audit/aggregate.py --per-spec           # one line per spec
docs/spec-audit/aggregate.py --not-true           # requirements with a wrong clause
docs/spec-audit/aggregate.py --fate needs-test    # requirements with one fate
grep '"spec": "firewall"' docs/spec-audit/requirements.jsonl
```

## `requirements.jsonl`

- `requirement`: the requirement's title, verbatim.
- `scenarios`: how many scenarios sit under it.
- `subject`: what implements the behaviour.
  - `python`, `shell`, `workflow-yaml`, `dockerfile-compose`, `config`
  - `prose-rulebook`: a `SKILL.md`, `*.agent.md`, or `AGENTS.md` an agent
    follows
  - `external`: a third-party system or a setting outside the repository
  - `mixed`: more than one of these. The OpenCode bridge's TypeScript is
    recorded as `mixed`.
- `truth`: judged against the checkout.
  - `true`: every clause holds.
  - `partial`: at least one clause is contradicted or has no implementation.
  - `false`: the central claim is contradicted.
  - `unverifiable`: nothing in the repository can confirm or refute it.
- `truth_note`: what differs, with an anchor. Present on every row that is not
  `true`, and on `true` rows with a smaller looseness.
- `test`: what executable thing enforces the behaviour.
  - `direct`: a test runs it and would fail if it broke.
  - `partial`: tests cover some clauses or scenarios.
  - `indirect`: tests reach the code without asserting this behaviour.
  - `static-gate`: a schema, linter, or CI step that is not a test.
  - `text-check`: the only check reads a file's text.
  - `none`
- `test_ref`: the best test or gate, as `path::test_name`.
- `scenarios_tested`: how many of its scenarios a test exercises.
- `adds`: what the requirement tells a reader that the implementation and its
  tests do not.
  - `nothing`
  - `summary`: gathers behaviour spread over several files.
  - `intent`: a guarantee the code meets without announcing.
  - `why`: a reason or a rejected alternative.
  - `external-contract`: a fact about a third-party system.
- `fate`: where the content goes if the spec is deleted.
  - `drop-tested`: delete; a test states it.
  - `drop-prose-duplicate`: delete; a second prose copy of a rulebook.
  - `drop-restates`: delete; the implementation reads plainly.
  - `needs-test`: executable, worth keeping, and untested.
  - `adr`: a decision record.
  - `code-comment`: a short invariant at the implementation.
  - `user-doc`: a README or guide.
  - `no-home`: none of the above.
- `fate_note`: what the test, record, or comment has to say.

## `rationale.jsonl`

- `title`: the entry's heading, verbatim.
- `kind`: `decision-with-alternatives`, `decision-only`, `external-constraint`,
  or `restates-behaviour`.
- `accurate`: `true`, `false`, or `unverifiable` — whether the decision still
  matches the code. `accurate_note` says what differs.
- `adr_worthy`: whether it would stand as a decision record a new developer
  needs.
- `rejected_count`: how many rejected alternatives it lists.

## `specs.jsonl`

- `dominant_subject`: the `subject` most of its requirements have.
- `glossary_terms`: project terms the spec defines or leans on, each with a
  `term` and a `meaning`.
- `duplicates`: other places that state the same behaviour in prose.
- `inbound_use`: code, skills, or agent definitions that cite or depend on the
  spec.
- `worst_drift`: its most consequential mismatch with the code.
- `verdict`: what deleting the spec with nothing written in its place would
  lose.
