# The first principles

The first principles of developing for agents (designing skills, plugins) and with agents (building production apps).

## TL;DR

It is a communication problem.
You are talking to a new hire in each new session.
Your AGENTS/CLAUDE.md, memory, skills, agent prompts - are what agent just finished reading,
aka the full day briefing for a new hire, he read it all, but doesn't mean it will recall every statement and change behavior exactly.

## It is a communication problem

In order to achieve good results you need to make sure agent is on the same page with human it talks to.

### Understand your audience

Each agent starts fresh. Like a new hire in a company.
Different model gives different behavior, knowledge basis is different too. That affects their approach to executing tasks

Each time you switch to new session, you talk to someone new (different seed + harness updates, system prompts change, etc). Agent memory and skills try to steer agent in the right direction, but it's not guaranteed. The more agent dives into the task, the less it will remember of where it started. As context fills up it gets worse exponentially at about 1/4 of capacity. At 1/2 the context capacity agent is pretty much useless. Yes it can forget it was following a task list, unless it used external tool to track progress.

You need to reteach it: compact, load skills needed right now.

### How to write

All agent files like any good software system follow DRY, YAGNI, KISS principles
