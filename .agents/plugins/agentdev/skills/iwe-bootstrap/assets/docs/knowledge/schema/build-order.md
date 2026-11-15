# Build order

An active plan, a pending or planned bug, and a pending backlog task can have a
`rank`. The `rank` is a positive integer. It gives the place of the item in one
build order that the three types share. A lower `rank` comes first.

``` yaml
rank: 300 # optional; positive integer
```

- The sequence is
  `iwe find --filter '{rank: {$exists: true}}' --sort rank:1 -f keys`. An item
  without `rank` is not in the sequence. The query `rank: {$exists: false}`
  finds these items.
- Ranks increase in steps of 100. An item that goes between two others takes the
  midpoint of their ranks. Only a reorder pull request changes the `rank` of
  more than one item.
- A done or cancelled item has no `rank`. The session that closes the item
  removes it.
- Equal ranks are valid. The key decides their order, and CI gives a warning.
