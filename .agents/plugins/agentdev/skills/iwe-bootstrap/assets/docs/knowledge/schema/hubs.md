# Hubs

A hub is the list of the live documents of one type. Each document type has one
hub, and the hub set is closed: `[schemas.hub]` in `.iwe/config.toml` lists it,
so adding a hub means adding it there.

- Frontmatter: `type: hub` and `stage: living`.
- Body: an H1, then one flat list of inclusion links, one for each member. The
  list is sorted by the key of the member, with a `YYYYMMDD-` prefix removed. A
  hub has no `##` section: `.iwe/schemas/hub.yaml` rejects one, and a test
  checks the order.
- The `description` of a hub names the document in `schema/` that defines its
  members. A hub gives no rule.
- A hub lists live documents only; links and queries reach the archived ones. It
  changes only when a member is created, archived, or renamed, never for a
  change of stage or priority, so two pull requests conflict on a hub only when
  their members sort next to each other.
