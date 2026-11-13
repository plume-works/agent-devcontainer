---
type: guide
description: 'Example guide: the steps a contributor follows to cut a Pomodux release build.'
---

# Cut a release build

*Example document — this shows the shape of a guide: one procedure a contributor
follows. The setup skill deletes `*.example.md` files after onboarding.*

1. Run the test suite and confirm it passes.
2. Build the installers for every platform the product doc lists.
3. Smoke-test one installer: start a focus session and let it complete.

*Convention notes: a guide carries `type: guide` and no stage. Every code anchor
in a guide is resolved on every commit, so a guide that names a script fails the
check the moment the script is renamed.*
