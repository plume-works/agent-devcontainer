---
name: iwe-setup
description: Brownfield-first workspace onboarding — scan the codebase and draft data/product.md plus starting guide docs from what the code shows, interview the developer only for what the code can't answer, mark the onboarding tasks done, and delete the example documents. Use when the user says "run the setup", "set up the workspace", or when product.md still contains ✏️ placeholders.
disable-model-invocation: true
---

# Workspace setup

Turn the blank workspace into this project's memory. The codebase is the
primary source — read it first and draft from evidence; ask the developer only
what the code can't answer. Every future session reads what you write here.

## Steps

1. **Assess.** Read `data/product.md`. List which ✏️ blocks are unfilled. If
   everything is filled, ask what to revise instead of re-onboarding.
2. **Locate the codebase.** Ask where the project's code lives (often the
   parent or a sibling directory of this workspace, or this workspace may sit
   inside the repo itself). If the project is greenfield — no code yet — skip
   to step 4 and run the interview alone.
3. **Scan.** Read the repository's README, package manifests, build
   configuration, entry points, directory layout, and test setup. Draft from
   what you find:
   - `data/product.md` — What is it, Platforms, Stack from direct evidence;
     leave ✏️ plus a concrete question under any section the code can't
     answer (Users, Constraints usually need the developer).
   - Propose (don't yet write) a `data/guides/<slug>.md` for each procedure a contributor must
     follow that the README does not already give — building, testing,
     releasing.
4. **Interview.** Ask in batches, conversationally:
   - _Product_: the one-liner; who uses it and for what; who it's not for.
   - _Reality_: current stage, what's shipped vs. aspirational, the next thing
     they intend to build.
   - _Constraints_: performance budgets, compatibility promises, licensing,
     privacy — anything every plan must respect.
   - _Rules_: recurring instructions they find themselves repeating to agents
     or contributors — these become the Authoring rules section.
5. **Write.** Fill every `data/product.md` section, deleting the italic
   instruction lines as sections fill; add a dated entry to its Changelog.
   Write the guides the developer approved, and link each from
   `data/guides.md`. Write no spec. A
   measurement the scan made that settles nothing yet goes to
   `data/findings/<slug>.md`, linked from `data/findings.md`.
6. **Close the loop.** Mark the finished onboarding task `fill-product-doc`:
   `iwe update -k data/backlog/<slug> --set stage=done --set completed=<today>`,
   remove any `rank` it carries, move it with
   `iwe rename data/backlog/<slug> data/archive/next-release/backlog/<slug>`,
   and remove its link from `data/backlog.md`. Delete the example
   docs — every `*.example.md` under `data/` (`iwe delete <key>` per doc).
   `iwe delete` removes their inclusion links from hubs automatically but
   _flattens_ inline links to plain text: sweep the hub files and remaining
   docs for leftover de-linked example lines and remove them.
7. **Validate & commit.** `iwe normalize`, then `iwe schema validate` — both
   must pass clean. Commit with a message like
   `setup: product doc filled, first guides drafted, examples removed`.

## Rules

- Never invent — every drafted statement must trace to the code or the
  developer's answer; "unknown" beats plausible fiction.
- Never leave a ✏️ block half-filled — ask follow-ups until each section is
  concrete, but let the user say "skip for now" (leave the ✏️ so the gap stays
  visible).
- Propose each guide in one line, and get the developer's approval before you
  write it.
- Don't delete the examples until real documents exist for the developer to
  learn the conventions from (product.md filled is the minimum).
