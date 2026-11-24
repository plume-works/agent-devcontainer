# Review rules

## Terms

- **Explicit request**: names the change it wants.
- **Question**: asks something; may be a finding phrased as a question.
- **Suggestion**: proposes an alternative; the author decides.
- **Observation**: remarks without asking; may need no action.

## Raise

1. Correctness and behavioral regressions, with an input the code really
   receives and the wrong result it produces.
2. Missing or weak tests for changed behavior.
3. Maintainability risks that materially raise future cost.
4. Security or performance issues with concrete impact.
5. Violations of a rule you can quote.

## Do not raise

- Taste, style a formatter owns, or alternatives not shown to be better.
- Speculation: a fault with no input that reaches it.

A comment or PR description calling a behavior deliberate is evidence, not a
verdict.

## Write

- Point at the place, say what breaks and why, suggest a fix.
- Keep the tone about the code.
- Ask when the code does not show its intent and the answer decides whether
  it is wrong.

## What blocks

- Blocks: a wrong outcome, a security exposure, session residue a rule
  forbids, a PR title or description that misstates the change.
- Everything else does not block.

## Act on a finding

- Check it against the code, not against how sure the comment sounds.
- Holds: make the smallest change that answers it.
- Does not hold: reply with the evidence.
- Unclear: ask.
