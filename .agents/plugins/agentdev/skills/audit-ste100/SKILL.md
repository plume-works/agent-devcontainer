---
name: audit-ste100
description: Check prose against ASD-STE100 Issue 9 (Simplified Technical English) and report each break of the standard with a replacement. Use to check a file, the lines that a diff adds, or a plan draft against the prose rule. The skill only reports and edits no file. A check for durable-knowledge residue belongs to /agentdev:iwe-audit.
---

# ASD-STE100 audit

This skill checks prose against ASD-STE100 Issue 9, Simplified Technical English
(STE). Issue 9 is the only issue that this skill applies. Do not apply the rules
of a different issue.

## The source of the rules

The skill checks from your own knowledge of the standard. It holds no copy of
the standard and no copy of the ASD-STE100 dictionary. Report a word or a
sentence only when you know that it breaks the standard.

## What is prose

Prose is all text in the target, with three exceptions:

- Text in code formatting is not prose.
- Text in a fenced block is not prose.
- Quoted text is not prose.

Do not check text that is not prose.

## Scopes

The caller names the target and one of these scopes. When the caller names no
scope, use the file scope.

- **File scope.** Read the whole file.
- **Diff scope.** Read only the lines that the diff adds. Do not check a line
  that the diff does not add, also when that line breaks the standard.
- **Plan scope.** Read every section of the plan.

## What to check

Check each sentence of prose for these three types of break:

1. **A writing rule of the standard.** Examples:
   - A procedural sentence has more than 20 words.
   - A descriptive sentence has more than 25 words.
   - A paragraph has more than six sentences.
   - A noun cluster has more than three words.
   - A sentence uses the passive voice where the active voice is possible.
   - A verb has a form that the standard does not permit, such as an `-ing`
     form that is not part of a technical name.
   - A sentence uses a phrasal verb.
   - A sentence leaves out an article that it needs.
   - An instruction gives more than one action, and the actions do not occur
     at the same time.
2. **A word that the standard does not approve.** A word must be in the
   dictionary, with its approved meaning and part of speech, or it must be a
   technical noun or a technical verb. Use one word for one meaning.
3. **A project term that the glossary does not list.** A project term is a
   technical noun or a technical verb that has a meaning specific to the
   repository. Read `docs/knowledge/data/glossary.md` in the repository that
   you run in. If the glossary lists the term, the term is correct. If the
   glossary does not list the term, report it, and give a word that the
   standard approves or a glossary entry to add. If the repository has no
   glossary, report that one time.

## Report

Give one table, with one row for each break:

| Place | Text | Rule | Replacement |
| ----- | ---- | ---- | ----------- |

- **Place** is an anchor: `path#heading-slug` in Markdown, `path::symbol` in
  code. Do not give a line number.
- **Text** is the prose that breaks the standard, quoted exactly.
- **Rule** is the rule or the dictionary entry that the text breaks.
- **Replacement** is text that obeys the standard and keeps the meaning.

When you find no break, write only this sentence: `No findings.`

## Rules

- Edit no file in any scope. The skill only reports. The caller decides what
  to change.
- Report each break one time.
- Keep the meaning of the text in each replacement.
