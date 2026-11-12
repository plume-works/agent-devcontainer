---
type: task
created: 2026-11-12
stage: pending
priority: medium
description: After the single-home plan ships, reduce the knowledge base to an issue tracker and architecture decision records, with code and executable tests as the only statement of behaviour.
sources:
- resource: docs/knowledge/data/plans/20261112-knowledge-base-single-home.md
- resource: docs/knowledge/data/spec/firewall.md
- resource: docs/knowledge/data/spec/xpra-port-forwarding.md
---

# Shrink the knowledge base to an issue tracker and decision records

The repository owner decided on 2026-11-12 that code and executable tests are
the only source of truth for behaviour, and that the knowledge base keeps two
jobs: tracking work (bugs, tasks, plans) and recording architecture decisions.
Specs stop being a statement of behaviour.

The decision rests on a comparison of three specs with their code: one matched,
and two had drifted. The drift is filed as [Bug: the firewall spec misstates the
enabled policy](../bugs/firewall-spec-misstates-enabled-policy.md), [Bug: the
enabled firewall leaves IPv6 open when ip6tables is
missing](../bugs/firewall-ipv6-open-without-ip6tables.md), [Bug: wildcard
firewall allowlist entries never take
effect](../bugs/firewall-wildcard-allowlist-entries-never-apply.md), and [Bug:
AGENTDEV_XPRA_PORT does not change the port Xpra listens
on](../bugs/xpra-port-setting-ignored.md). The other 29 documents under
`data/spec/` have not been compared.

## Order

This work starts after [One home for each kind of
knowledge](../plans/20261112-knowledge-base-single-home.md) ships. The
repository owner wants that plan executed in full first, so the graph holds a
complete record of how the knowledge base deteriorated before it is reduced.

## What to do

- Decide what replaces each requirement in `data/spec/`: an executable test
  where one can cover the behaviour, a decision record where the requirement
  states a choice and its reason, and deletion otherwise.
- Decide which document types remain and remove the schemas, hubs, and workflow
  skill steps that maintain the others.
- Write the plan with `/agentdev:iwe-plan`.
