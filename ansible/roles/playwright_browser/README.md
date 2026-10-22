# Playwright browser role

Installs a pinned Playwright command-line client, its matching Chromium browser,
and the required Linux libraries. Browser binaries live in `/opt/playwright`,
outside home-directory caches that devcontainer volumes can hide.

## Variables

| Variable                     | Default                 | Purpose                              |
| ---------------------------- | ----------------------- | ------------------------------------ |
| `playwright_browser_version` | See `defaults/main.yml` | Playwright package and browser pin.  |
| `playwright_browser_package` | `playwright`            | Bun package that provides the CLI.   |
| `playwright_browser_path`    | `/opt/playwright`       | Image-owned browser binary location. |

The role requires Bun and Node.js. Include it after `bun_setup` and `nodejs`.
It is opt-in through the calling playbook so base provisioning can omit the
browser payload.

The browser path remains writable after provisioning so a non-root runtime
user can install the browser build required by a project-owned Playwright
dependency.
