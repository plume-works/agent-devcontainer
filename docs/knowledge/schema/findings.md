# Findings

A finding is a measurement that does not yet settle a question. A finding is not
a design, and it gives no behaviour that the code must have.

- Path: `data/findings/<slug>.md`.
- Hub: `data/findings.md`.
- Frontmatter: `type: finding`. The schema does not accept a `stage`.

Body: `## Measurement` and `## Closing` are required, in this order. Other
sections can be there. A finding gives:

- the measurement;
- each hypothesis that was eliminated, and what eliminated it;
- what can settle the question;
- what closes the finding. "Not worth the cost" is a valid closing, and the
  finding records it as a decision.

A finding has its own document. The document that the question came from keeps
no summary of the finding, no section about it, and no link to it. The one
exception is its status line, and only when the finding changes its own
acceptance. A reference points from the newer document to the older document.
