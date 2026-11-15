# Index file

`data/index.md` is a reserved filename of OKF, not a concept document. It has no
`type`, and `okf-index.yaml` checks it. Its only frontmatter is
`okf_version: "0.2"`. The body is `#` sections of link bullets. Each bullet is a
Markdown link to a hub or a tracker, then `-`, then the `description` of that
document.

The index lists hubs and trackers, never their members, so it changes only when
a hub is added or removed. The graph has no `data/log.md`, which OKF makes
optional.
