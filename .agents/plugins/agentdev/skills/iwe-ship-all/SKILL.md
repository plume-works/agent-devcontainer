---
name: iwe-ship-all
description: Ship all implemented plans in the IWE graph
---

# Ship all implemented plans in the IWE graph

You are the coordinator. Discover all plans that have been implemented but not shipped yet. Identify cross dependencies. Run one subagent per plan sequentially in the order of their dependencies with `/agentdev:iwe-ship <plan_file_path>` as prompt. Allow subagent to load AGENTS.md/CLAUDE.md with guidance. Re-post their final output/summary here.
