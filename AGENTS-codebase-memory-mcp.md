# codebase-memory-mcp

## distrust hotspot `fan_in`

`get_architecture`'s `hotspots` aspect can report an inflated `fan_in` on the wrong node when a
short/common function name (e.g. `main`, `usage`, `run`) exists in more than one language or file
in this repo (e.g. a Bash script's `main` vs. `validate_agent_files/main.py:main`). The count
appears to aggregate by bare name rather than resolved qualified node, and gets attributed to
whichever node — real in-degree may be 1 while `fan_in` claims 40+. This is a known upstream bug:
[DeusData/codebase-memory-mcp#725](https://github.com/DeusData/codebase-memory-mcp/issues/725).

Before treating a `hotspots` entry as real, verify it with a query scoped to the exact qualified
name — `trace_path(function_name=<qualified_name>, direction="inbound")` or a direct
`query_graph` `MATCH ... RETURN count(r)` — and trust that number instead.
