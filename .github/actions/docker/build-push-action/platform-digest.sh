#!/usr/bin/env bash
# Writes the digest output: the linux/$ARCH manifest inside $IMAGE@$DIGEST, or $DIGEST
# itself when it names a single manifest. A build FROM it keys on the image, not the index.
set -euo pipefail

raw="$(docker buildx imagetools inspect --raw "${IMAGE:?}@${DIGEST:?}")"
platform_digest="$(jq -er --arg arch "${ARCH:?}" --arg digest "$DIGEST" '
  if has("manifests") then
    [.manifests[] | select(.platform.os == "linux" and .platform.architecture == $arch)]
    | if length == 1 then .[0].digest
      else error("expected one linux/\($arch) manifest, found \(length)") end
  else $digest end' <<<"$raw")"
echo "digest=${platform_digest}" >>"${GITHUB_OUTPUT:?}"
