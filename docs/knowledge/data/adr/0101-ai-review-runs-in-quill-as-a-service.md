---
type: adr
stage: proposed
supersedes:
- adr/0037-ai-review-trusts-named-bots
- adr/0059-ai-reviews-requested-and-held-by-label
- adr/0069-trusted-bot-approval-checks-push-history
- adr/0099-responder-runs-on-pull-request-and-review-events
- adr/0100-ci-review-runs-the-image-catalog
---

# The AI review of this repository runs in quill-as-a-service

This repository has no AI review workflow. quill-as-a-service handles reviews. A
workflow is CI doing its best to act as a review service: every repository keeps
its own copy of it, with its actions, environment, secrets and labels. A
deployed service, as Greptile is, reviews every repository it is set up for.
