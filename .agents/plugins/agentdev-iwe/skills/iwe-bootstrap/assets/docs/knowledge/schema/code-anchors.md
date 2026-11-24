# Code anchors

An anchor names a place in a file. A document never records a line number: it is
wrong the next time the file changes.

- Code: `path@Class.method` or `path@function`.
- Markdown: `path#heading-slug`.
- YAML, JSON, and TOML: `path#key.path`. The `id` or the `name` of a list
  element identifies it.
- A Makefile or a Dockerfile: `path#target` or `path#stage`.
- A place inside one of these: the anchor, then ` › "verbatim quote"`.

The `path` is relative to the repository root. The writer takes each anchor from
the current checkout, never from memory. An anchor stays true until its target
is renamed or removed, and then it stops resolving, so it carries no date. A
line number gives no such signal.
