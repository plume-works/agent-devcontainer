---
type: adr
stage: proposed
supersedes:
- adr/0043-expo-bundle-leaves-the-workflow-to-expo-plugin
- adr/0054-setup-progress-in-root-file
---

# Template adoption has no skill

The catalog ships no skill that adopts or updates the agent-devcontainer
template in another repository. The `template-consume` skill, its consumption
guide, its optional bundles, and its `.agent.metadata.json` marker are removed.
The maintainer made this decision when the IWE workflow moved to its own plugin:
the skill read the `iwe-bootstrap` scaffold through a path inside `agentdev`,
and the maintainer no longer wanted the skill.

## Consequences

- A repository that wants the template copies it by hand. Nothing records which
  template commit it holds, and nothing reports template changes to it.
- The setup progress file and the Expo bundle, which only the skill wrote, have
  no writer.
