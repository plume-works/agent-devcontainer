---
type: adr
stage: accepted
---

# Renovate keeps pins current, after a wait

Renovate keeps pins current. Updates merge on their own once the build passes,
but only when the release is 3 days old, because the build cannot tell a bad
release from a good one. An `x.y.0` release waits 10 days, since those usually
have the most bugs. Renovate proposes updates once a day, during its daily
scheduled run, not on every push to `main`.

Our own images skip the wait and the daily window: they bump as soon as `edge`
moves. CI has already built and tested them, and their registry does not say
when a digest was published.

## Considered Options

- No wait.
- A wait for the npm-registry tools only.
- Skipping `x.y.0` releases entirely.
- Proposing updates on every run of the bot.
