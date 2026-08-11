# Perm Probe Role

Diagnostic role. Stats a set of shared system paths and emits one greppable
`PERM_PROBE` line per probe point, so an ownership change on a shared directory
can be attributed to the role that ran between two probes.

It exists to hunt a specific failure: `/usr/local/bin` acquiring an owner that
resolves to no passwd entry (`owner=UNKNOWN`), which breaks later installs that
write there. Because the culprit is a numeric uid/gid baked into a third-party
archive rather than an explicit `chown`, the probe shells out to `stat -c` and
reports raw numeric ids — `ansible.builtin.stat` would hide the signal behind
name resolution.

## Usage

Interleave between the roles under investigation, giving each probe a label:

```yaml
roles:
  - { role: perm_probe, perm_probe_label: 'before bun_setup', tags: ['always'] }
  - { role: bun_setup, tags: ['bun_setup'] }
  - { role: perm_probe, perm_probe_label: 'after bun_setup', tags: ['always'] }
```

A role must be listed more than once in a `roles:` block to run more than once,
which Ansible allows only when the invocations differ — the distinct
`perm_probe_label` per probe is what makes each one execute.

## Reading the output

Filter a build log down to the probe trail:

```bash
grep PERM_PROBE build.log
```

Each probe prints a report line per path. The offending role is the one between
the last clean probe and the first `PERM_PROBE DRIFT` line.

## Variables

| Variable                   | Default                                                              | Purpose                                           |
| -------------------------- | -------------------------------------------------------------------- | ------------------------------------------------- |
| `perm_probe_label`         | `unlabeled`                                                          | Identifies the probe point in every emitted line. |
| `perm_probe_paths`         | `/usr/local/bin`, `/usr/local`, `/usr/local/lib`, `/usr/local/share` | Paths to stat.                                    |
| `perm_probe_expected_uid`  | `0`                                                                  | Owner uid every probed path should hold.          |
| `perm_probe_expected_gid`  | `0`                                                                  | Owner gid every probed path should hold.          |
| `perm_probe_fail_on_drift` | `false`                                                              | Abort the play at the first drifting path.        |

Setting `perm_probe_fail_on_drift: true` stops the run at the culprit instead of
continuing through later roles, which keeps the container in the broken state
for inspection. Leave it `false` for a full trail across every role.

## Removal

This role is scaffolding for an active investigation, not a permanent part of
the provisioning flow. Remove the interleaved probes from `setup-dev.yml` once
the cause is fixed.
