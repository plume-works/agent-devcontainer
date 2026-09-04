#!/usr/bin/env bash

set -euo pipefail
shopt -s nullglob

usage()
{
  cat <<'EOF'
Usage: scripts/download-claude-responder-runs.sh --start DATETIME --end DATETIME [options]

Downloads AI Responder runs and claude-responder-output artifacts for a UTC
datetime range. DATETIME values are parsed with GNU date and normalized to UTC.

Options:
  --start DATETIME       Inclusive range start, for example 2026-09-01T00:00:00Z.
  --end DATETIME         Inclusive range end, for example 2026-09-04T04:35:05Z.
  --repo OWNER/REPO      GitHub repository. Defaults to the current gh repo.
  --workflow NAME        Workflow file name or numeric id. Default: ai-responder.yml.
  --artifact-name NAME   Artifact to download. Default: claude-responder-output.
  --output DIR           Output directory. Default: ./.tmp/claude-review-costs.
  --limit N              Max matching runs to keep after API filtering. Default: 1000.
  -h, --help             Show this help.

Outputs:
  runs.json
  all-ai-responder-runs.csv
  artifacts/<run_id>.json
  claude-output-artifacts.json
  downloads/<run_id>/claude-execution-output.json
EOF
}

require_command()
{
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf '%s is required.\n' "$command_name" >&2
    exit 1
  fi
}

normalize_datetime()
{
  local value="$1"

  if ! date -u -d "$value" '+%Y-%m-%dT%H:%M:%SZ'; then
    printf 'Could not parse datetime: %s\n' "$value" >&2
    exit 2
  fi
}

repo=""
workflow="ai-responder.yml"
artifact_name="claude-responder-output"
output_dir="./.tmp/claude-review-costs"
limit="1000"
start=""
end=""

while (($#)); do
  case "$1" in
    --start)
      if [[ $# -lt 2 ]]; then
        echo "--start requires a value." >&2
        exit 2
      fi
      start="$2"
      shift 2
      ;;
    --end)
      if [[ $# -lt 2 ]]; then
        echo "--end requires a value." >&2
        exit 2
      fi
      end="$2"
      shift 2
      ;;
    --repo)
      if [[ $# -lt 2 ]]; then
        echo "--repo requires a value." >&2
        exit 2
      fi
      repo="$2"
      shift 2
      ;;
    --workflow)
      if [[ $# -lt 2 ]]; then
        echo "--workflow requires a value." >&2
        exit 2
      fi
      workflow="$2"
      shift 2
      ;;
    --artifact-name)
      if [[ $# -lt 2 ]]; then
        echo "--artifact-name requires a value." >&2
        exit 2
      fi
      artifact_name="$2"
      shift 2
      ;;
    --output)
      if [[ $# -lt 2 ]]; then
        echo "--output requires a value." >&2
        exit 2
      fi
      output_dir="$2"
      shift 2
      ;;
    --limit)
      if [[ $# -lt 2 ]]; then
        echo "--limit requires a value." >&2
        exit 2
      fi
      limit="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$start" || -z "$end" ]]; then
  echo "--start and --end are required." >&2
  usage >&2
  exit 2
fi
if ! [[ "$limit" =~ ^[1-9][0-9]*$ ]]; then
  printf -- '--limit must be a positive integer: %s\n' "$limit" >&2
  exit 2
fi

require_command gh
require_command jq
require_command date

gh auth status >/dev/null

if [[ -z "$repo" ]]; then
  repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
fi

start_utc="$(normalize_datetime "$start")"
end_utc="$(normalize_datetime "$end")"
if [[ "$start_utc" > "$end_utc" ]]; then
  printf 'Start must be earlier than or equal to end: %s > %s\n' "$start_utc" "$end_utc" >&2
  exit 2
fi

mkdir -p "$output_dir/artifacts" "$output_dir/downloads"

raw_runs="$output_dir/runs.raw.json"
runs_json="$output_dir/runs.json"
created_filter="${start_utc}..${end_utc}"

printf 'Listing %s runs in %s from %s through %s.\n' \
  "$workflow" "$repo" "$start_utc" "$end_utc" >&2
gh api \
  --paginate \
  --method GET \
  "repos/${repo}/actions/workflows/${workflow}/runs" \
  -f "created=${created_filter}" \
  -f per_page=100 \
  --jq '
    .workflow_runs[]
    | {
        databaseId: .id,
        displayTitle: .display_title,
        event,
        headBranch: .head_branch,
        headSha: .head_sha,
        conclusion: (.conclusion // ""),
        status,
        createdAt: .created_at,
        updatedAt: .updated_at,
        startedAt: .run_started_at,
        url: .html_url,
        workflowName: .name,
        attempt: .run_attempt
      }
  ' > "$raw_runs"

jq --argjson limit "$limit" -s 'sort_by(.createdAt) | reverse | .[0:$limit]' \
  "$raw_runs" > "$runs_json"

jq -r '
  (["run_id","created_at","event","conclusion","status","head_branch","title","url"]),
  (.[] | [
    .databaseId,
    .createdAt,
    .event,
    (.conclusion // ""),
    .status,
    (.headBranch // ""),
    .displayTitle,
    .url
  ])
  | @csv
' "$runs_json" > "$output_dir/all-ai-responder-runs.csv"

jq -r '.[].databaseId' "$runs_json" | while IFS= read -r run_id; do
  artifact_json="$output_dir/artifacts/${run_id}.json"
  if [[ ! -s "$artifact_json" ]]; then
    printf 'Fetching artifacts for run %s.\n' "$run_id" >&2
    gh api "repos/${repo}/actions/runs/${run_id}/artifacts" > "$artifact_json"
  fi
done

mapfile -t artifact_files < <(
  jq -r --arg artifacts_dir "$output_dir/artifacts" \
    '.[] | "\($artifacts_dir)/\(.databaseId).json"' "$runs_json"
)
if ((${#artifact_files[@]})); then
  jq -s --arg artifact_name "$artifact_name" '
    [
      .[]
      | .artifacts[]?
      | select(.name == $artifact_name)
      | {
          run_id: .workflow_run.id,
          artifact_id: .id,
          name,
          expired,
          created_at,
          expires_at,
          size_in_bytes
        }
    ]
    | {
        artifact_name: $artifact_name,
        count: length,
        expired: (map(select(.expired)) | length),
        unexpired: (map(select(.expired | not)) | length),
        artifacts: .
      }
  ' "${artifact_files[@]}" > "$output_dir/claude-output-artifacts.json"
else
  jq -n --arg artifact_name "$artifact_name" '{
    artifact_name: $artifact_name,
    count: 0,
    expired: 0,
    unexpired: 0,
    artifacts: []
  }' > "$output_dir/claude-output-artifacts.json"
fi

jq -r '.artifacts[] | select(.expired | not) | .run_id' \
  "$output_dir/claude-output-artifacts.json" | while IFS= read -r run_id; do
  destination="$output_dir/downloads/${run_id}"
  marker="$destination/.downloaded"
  mkdir -p "$destination"
  if [[ ! -e "$marker" ]]; then
    printf 'Downloading %s for run %s.\n' "$artifact_name" "$run_id" >&2
    gh run download "$run_id" \
      --repo "$repo" \
      --name "$artifact_name" \
      --dir "$destination"
    touch "$marker"
  fi
done

jq -n \
  --arg repo "$repo" \
  --arg workflow "$workflow" \
  --arg start "$start_utc" \
  --arg end "$end_utc" \
  --slurpfile runs "$runs_json" \
  --slurpfile artifacts "$output_dir/claude-output-artifacts.json" \
  '{
    repo: $repo,
    workflow: $workflow,
    start_utc: $start,
    end_utc: $end,
    runs: ($runs[0] | length),
    artifacts: $artifacts[0].unexpired
  }'
