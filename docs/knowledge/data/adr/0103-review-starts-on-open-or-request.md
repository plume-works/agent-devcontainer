---
type: adr
stage: proposed
supersedes:
- adr/0059-ai-reviews-requested-and-held-by-label
---

# A review starts on open or on request

The AI reviewer reviews a pull request when it opens, is reopened, or leaves
draft, and when `request-ai-review` is added. It never reviews on a push alone.
A new review withdraws the reviewer's earlier approval.

## Considered Options

- A review on each push. Rejected: a busy pull request costs a model run for
  each push.
- Assign the App or request it as a reviewer. Rejected: GitHub allows neither
  for a GitHub App.
