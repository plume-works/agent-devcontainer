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
- what closing the finding looks like. "Not worth the cost" is a valid closing,
  and the finding records it as a decision rather than leaving it to lapse.

A finding has its own document: a question that the original work did not scope
goes in a new document. The document that the question came from keeps no
summary of the finding, no section about it, and no forward link to it. The one
exception is the status line of that document, and only when the finding affects
that document's own acceptance. References point from the newer document to the
older one.
