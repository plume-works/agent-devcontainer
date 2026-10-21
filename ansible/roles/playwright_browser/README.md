# Playwright browser role

Installs a pinned Playwright command-line client, its matching Chromium browser,
and the required Linux libraries. Browser binaries live in `/opt/playwright`,
outside home-directory caches that devcontainer volumes can hide.

## Variables

| Variable                     | Default           | Purpose                              |
| ---------------------------- | ----------------- | ------------------------------------ |
| `playwright_browser_version` | `1.64.0`          | Playwright package and browser pin.  |
| `playwright_browser_package` | `playwright`      | Bun package that provides the CLI.   |
| `playwright_browser_path`    | `/opt/playwright` | Image-owned browser binary location. |

The role requires Bun and Node.js. Include it after `bun_setup` and `nodejs`.
It is opt-in through the calling playbook so base provisioning can omit the
browser payload.
