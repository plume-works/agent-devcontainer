---
type: finding
description: 'Example finding: the completion notification arrives late on some Linux desktops, and what would settle why.'
---

# Notification latency on Linux

*Example document — this shows the shape of a finding: a measurement, the
hypotheses it eliminated, and what closing it looks like. The setup skill
deletes `*.example.md` files after onboarding.*

## Measurement

On two of five Linux desktops tested, the completion notification appeared 2–4
seconds after the timer reached 00:00; the session itself was recorded on time.

## Hypotheses eliminated

- **The timer fires late** — the session log records the completion at 00:00 on
  every machine.

## Closing

Closed when the delay is traced to the notification daemon or to Pomodux, or
judged not worth the cost: a delay this size changes no decision of the [timer
ADR](../adr/0001-timer-counts-wall-clock-time.example).

*Convention notes: a finding carries `type: finding` and no stage, and states no
behaviour the code must meet. When it settles into a decision, the decision goes
to an ADR that a plan proposes.*
