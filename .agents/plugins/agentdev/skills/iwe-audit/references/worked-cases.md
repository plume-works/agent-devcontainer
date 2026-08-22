# Worked cases

Each case is real text from an audited repository, with the judgment that
applied to it. The point of reading them is calibration: the same pattern
produces a DROP in one sentence and a REWRITE in the next.

## Provenance carrying a real fact

> Two trigger behaviors surprise people, and both cost a debugging session here:
>
> - The `pull_request` triggers are `opened`, `reopened`, `assigned`, and
>   `ready_for_review` — **not `synchronize`**. Pushing new commits does not
>   re-run the responder.

**Verdict: DROP the heading, KEEP the bullet.**

`cost a debugging session here` dates the text to one afternoon, and
`surprise people` generalizes from a single incident to a claim about readers.
The trigger list underneath is a durable interface fact and survives untouched.

Deleting the whole block because its first line is residue is the most common
way this audit does damage.

## An argument with a draft nobody saw

> Waiving the requirement is a separate statement of trust, so it is spelled out
> as a list rather than inferred from the author being a bot.

**Verdict: REWRITE.**

The rejected alternative — inferring from the author type — exists only in an
earlier draft of the same file. No reader can see what the sentence is replying
to, so the clause spends its length defending a choice nobody is contesting.

> Waiving the requirement is a statement of trust: the exemption names its
> authors explicitly.

Then verify that the code actually names them, and cite the line. The rewrite is
not finished until it does.

## Dated tool behavior standing in for a decision

> `claude-code-action` refuses a bot actor outright ("Workflow initiated by
> non-human actor"), so the run could only ever end red.

**Verdict: DROP.**

This is the observed behavior of a third-party tool on one day, quoting its
error text. It goes stale the moment that tool adds a configuration flag — and
it displaced the actual reason, which was a decision that dependency bumps do
not need review at all.

Recording an obstacle in place of a decision makes deliberate policy read as a
workaround, and the next reader will try to remove the workaround.

## The adverb that asserts nothing

Across one knowledge base, `deliberate` and `deliberately` appeared 33 times in
19 files — three in a single section. The word is addressed to a future editor
who might change the line, not to a reader who needs to understand it. It is the
same impulse that produces defensive comments, relocated into prose.

Both verdicts occur:

> This gate is deliberate — it stops the workflow running in forks.

**REWRITE** to `This gate stops the workflow running in forks.` The adverb adds
nothing the sentence did not already carry.

> This is deliberate — a review per commit would be prohibitively expensive.

**REWRITE** to lead with the constraint: `A review per commit would be
prohibitively expensive.` The cost is the load-bearing part; verify it is still
the operative reason before keeping it.

## Churn as a detector

One specification section was rewritten in three consecutive commits as the
underlying decision changed, growing each time. Successive drafts had each left
their reasoning in place, so the section argued for a policy, against the policy
it replaced, and against the one before that.

Where commit history is available, `git log --follow --stat` over a document
finds these quickly. A section that grew on every rewrite is tracking session
history rather than recording a decision.
