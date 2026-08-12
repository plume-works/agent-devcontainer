# Perm Probe Role

Stats a set of shared system paths and emits one greppable `PERM_PROBE` line per
probe point, failing the play when a path is owned by anyone but root.

`setup-dev.yml` runs it once, last, as a build guard. A third-party release
archive can carry its build runner's numeric uid/gid and silently chown the
directory it unpacks into, handing a shared system directory to an account that
does not exist on the target. That is not hypothetical: zizmor's tarball did
exactly this to `/usr/local/bin` (uid/gid 1001), which broke every later install
writing there — including `codebase-memory-mcp`, whose activation staging
refuses a target directory with an unexpected owner.

The guard has to run in the build because a bad ownership baked into the
published image is inherited by every warm build layered on top of it. Once it
ships, the image reproduces the breakage even after the offending role is fixed,
so the failure must stop the build rather than reach the registry.

The probe shells out to `stat -c` rather than using `ansible.builtin.stat`: the
raw syscall reports numeric uid/gid verbatim, while the module hides the signal
behind name resolution — and an owner resolving to no passwd entry is precisely
the signal.

## Guard usage

One invocation after every other role, configured to fail:

```yaml
roles:
  # ... all provisioning roles ...
  - {
      role: perm_probe,
      perm_probe_label: 'final',
      perm_probe_fail_on_drift: true,
      tags: ['always'],
    }
```

On drift the play stops with the offending path, its numeric owner, and mode:

```text
PERM_PROBE DRIFT [final] expected uid=0 gid=0, found:
  ['/usr/local/bin uid=1001 gid=1001 user=UNKNOWN group=UNKNOWN mode=755']
```

## Bisect usage

When the guard fires, the report names the path but not the role that changed
it. To find that, temporarily interleave probes between roles, giving each a
distinct label, and leave `perm_probe_fail_on_drift` at its default so the run
continues and produces a full trail:

```yaml
roles:
  - { role: perm_probe, perm_probe_label: 'before bun_setup', tags: ['always'] }
  - { role: bun_setup, tags: ['bun_setup'] }
  - { role: perm_probe, perm_probe_label: 'after bun_setup', tags: ['always'] }
```

A role must be listed more than once to run more than once, which Ansible allows
only when the invocations differ — the distinct `perm_probe_label` is what makes
each probe execute.

Then filter the build log:

```bash
grep PERM_PROBE build.log
```

The culprit is the role between the last clean probe and the first
`PERM_PROBE DRIFT` line. Remove the interleaved probes once found; only the
final guard is permanent.

Bisect from a base image whose paths are already root-owned. Starting from an
image that inherited the damage reports drift at the baseline probe and
implicates no role.

## Variables

| Variable                   | Default                                                              | Purpose                                           |
| -------------------------- | -------------------------------------------------------------------- | ------------------------------------------------- |
| `perm_probe_label`         | `unlabeled`                                                          | Identifies the probe point in every emitted line. |
| `perm_probe_paths`         | `/usr/local/bin`, `/usr/local`, `/usr/local/lib`, `/usr/local/share` | Paths to stat.                                    |
| `perm_probe_expected_uid`  | `0`                                                                  | Owner uid every probed path should hold.          |
| `perm_probe_expected_gid`  | `0`                                                                  | Owner gid every probed path should hold.          |
| `perm_probe_fail_on_drift` | `false`                                                              | Abort the play at the first drifting path.        |

A path that does not exist is not drift — the probe reports only what it can
stat, so listing a path absent on some builds is safe.
