---
type: adr
stage: proposed
---

# An AI review run keeps every transcript and a report built from them

A pull request review dispatches its passes and validators as subagents, each
with its own transcript, and a reader of a run needs to see what each one was
asked, what it found, and why a finding was dropped. Every responder run keeps
all of its agent transcripts, and its run report is generated from those
transcripts by a script rather than written by the reviewing model. A report
derived from the transcripts cannot disagree with what ran and costs no model
tokens; the review writes into its transcript only the facts no tool call would
otherwise record. See ADR-0101 for the review service this extends.

## Considered Options

- The reviewing model writes the report itself. Rejected: its account can drift
  from what the subagents actually returned, and every run pays for it in
  tokens.
