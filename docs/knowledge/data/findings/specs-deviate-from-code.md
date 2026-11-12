---
type: finding
description: Two of three specs compared with their code state behaviour the code does not have; three of the five differences are code defects and two are stale spec text.
sources:
- resource: docs/knowledge/data/spec/agent-file-discovery.md
- resource: docs/knowledge/data/spec/firewall.md
- resource: docs/knowledge/data/spec/xpra-port-forwarding.md
- resource: py_packages/validate_agent_files/validate_agent_files/loaders.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/xpra.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/health.py
- resource: .devcontainer/firewall-allowlist.txt
---

# Specs deviate from the code they describe

## Measurement

Three of the 32 documents under `data/spec/` were compared, requirement by
requirement, with the code each one names in `sources`.

| Spec                                                    | Result       |
| ------------------------------------------------------- | ------------ |
| [Agent file discovery](../spec/agent-file-discovery.md) | matches      |
| [Firewall](../spec/firewall.md)                         | 4 deviations |
| [Xpra port forwarding](../spec/xpra-port-forwarding.md) | 1 deviation  |

### Firewall: which values enable it

The spec enables the firewall only for `ENABLE_FIREWALL=true` and calls every
other value inert with exit 0. That holds for a direct
`agentdev-runtime firewall apply`. At container start,
`py_packages/agentdev_runtime/agentdev_runtime/supervisor.py::run` sets
`ENABLE_FIREWALL` to `true` whenever
`py_packages/agentdev_runtime/agentdev_runtime/settings.py::Settings.boolean`
accepts the value, so `1`, `yes`, and `on` enable it too, and an unrecognised
value is a configuration error. Stale spec text.

### Firewall: IPv6 stays open without ip6tables

The spec requires the enabled firewall to block IPv6 entirely and to fail loudly
when misconfigured.
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::block_ipv6` prints
`WARNING: ip6tables not available; IPv6 traffic is not restricted` and returns
when `ip6tables` is not on `PATH`, and
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::verify` never forces
an address family, so the command exits 0. Calling `block_ipv6` with a
`firewall.System` whose `has` returns `False` shows it: the warning, no command
run, no `FirewallError`. Code defect.

### Firewall: wildcard allowlist entries never apply

The spec admits the hosts on the allowlist. `DOMAIN_RE` in
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py` admits a leading
`*.`, so
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::validate_allowlist`
accepts `*.gallery.vsassets.io` and `*.gallerycdn.vsassets.io` from
`.devcontainer/firewall-allowlist.txt`.
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::add_entry` then
resolves the entry as a host literally named `*.<domain>`, which fails, and
skips it with `WARNING: Failed to resolve *.gallery.vsassets.io (skipping)`. The
policy is an `ipset` of IPv4 addresses resolved once, which cannot express every
host under a domain. Code defect.

### Firewall: what the policy admits and how it refuses

The spec admits only allowlisted hosts and says a connection to any other host
is dropped.
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply_policy` also
accepts all traffic to and from the default gateway, which is the Docker host,
and ends `OUTPUT` with `REJECT --reject-with icmp-admin-prohibited`, so a
refused connection fails at once. In the deploy profile
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply` refuses to
start without `AGENTDEV_TRUSTED_PROXY_CIDRS` and admits those sources to the
OpenCode and Xpra ports, and in both profiles it applies the allowlist again to
nested containers. The firewall spec is silent on all three, and [Standalone
OpenCode runtime](../spec/standalone-opencode-runtime.md) covers them in one
clause with no scenario. Stale spec text.

### Xpra: the port setting has no effect on Xpra

The spec fixes the port at 14500 with `--port` as the only override.
`py_packages/agentdev_runtime/agentdev_runtime/xpra.py::parse` does that, and
both `supervisord.conf` files start `agentdev-runtime xpra --supervised` with no
`--port`. `py_packages/agentdev_runtime/agentdev_runtime/settings.py` still
declares `AGENTDEV_XPRA_PORT` as "Xpra port.", and the Xpra probe in
`py_packages/agentdev_runtime/agentdev_runtime/health.py` and the proxy-ingress
rule in `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply` read
it. With `AGENTDEV_XPRA_PORT=15000`, `xpra.parse([]).port` is `14500` while
`Settings().get('AGENTDEV_XPRA_PORT')` is `15000`: Xpra stays on 14500 and the
probe and the firewall rule move. Code defect.

## Hypotheses eliminated

- **The wildcard entries fail only because of the DNS resolver where the check
  ran.** `socket.getaddrinfo('x.gallery.vsassets.io', None, socket.AF_INET)`
  returned addresses on the same machine where `*.gallery.vsassets.io` failed.
- **The deviations are wording only.** Three of the five change what a running
  container does.

## What would settle it

- Whether the IPv6 gap can occur in a shipped image: check for `ip6tables` in
  the published images. `ansible/roles/devcontainer_firewall/tasks/main.yml`
  installs the `iptables` package, which normally provides it.
- Whether the rate holds across the graph: compare the other 29 specs the same
  way. Nothing here measures them.
- None of the three code defects was observed in a running container with the
  firewall enabled; each was shown by calling the function with stubbed system
  calls.

## Closing

This finding closes when each of the three code defects is fixed or declined as
a recorded decision. The two stale spec passages are not corrected on their own:
[Shrink the knowledge base to an issue tracker and decision
records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md) decides what
happens to every spec. Comparing the other 29 specs is not part of closing.
