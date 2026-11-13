---
type: someday
description: Check prose against the full ASD-STE100 Issue 9 standard, its dictionary included, in place of the model's own knowledge of the standard.
sources:
- resource: https://www.asd-ste100.org/
- resource: docs/knowledge/data/backlog/migrate-prose-to-ste100.md
---

# Full ASD-STE100 compliance

The `audit-ste100` skill checks prose from the model's own knowledge of
ASD-STE100 Issue 9. The repository holds no copy of the standard and no copy of
its dictionary. The repository owner decided that for the first version of the
rule, because the standard is a 434-page document.

The idea is to check prose against the standard itself:

- write the rules that `audit-ste100` applies from the Issue 9 document;
- check each word against the Issue 9 dictionary.

The dictionary is a document that ASD owns. A decision on this idea needs the
terms under which ASD permits a copy in a repository or in CI.
