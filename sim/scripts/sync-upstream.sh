#!/usr/bin/env bash
# Re-sync engine/twinleaf/src with upstream twinleafgg (ptcg-server/src) at a given commit.
#   bash scripts/sync-upstream.sh [commit=main]
# Files carrying a "[winner patch" marker are never overwritten: if upstream changed one of them,
# the script lists it so the patch can be re-applied by hand. Afterwards run `npm test`; new or
# changed cards are checked automatically, then record them with `npm run cards:baseline`.
set -euo pipefail
REF="${1:-main}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="$HERE/../engine/twinleaf"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone --quiet --filter=blob:none --no-checkout https://github.com/twinleafgg/twinleafgg.git "$TMP/up"
git -C "$TMP/up" sparse-checkout init --cone
git -C "$TMP/up" sparse-checkout set ptcg-server
git -C "$TMP/up" checkout --quiet "$REF"
NEW="$TMP/up/ptcg-server/src"
conflicts=()
while IFS= read -r -d '' f; do
  rel="${f#$NEW/}"
  dst="$ENGINE/src/$rel"
  if [ -f "$dst" ] && grep -q "\[winner patch" "$dst"; then
    # keep our patched file; flag it if upstream's version differs from the one we patched
    conflicts+=("$rel")
    continue
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$f" "$dst"
done < <(find "$NEW" -type f -print0)
cp "$TMP/up/ptcg-server/package.json" "$TMP/up/ptcg-server/tsconfig.json" "$ENGINE/"
git -C "$TMP/up" log -1 --format='%H %ci' > "$ENGINE/.upstream_commit"
echo "synced to $(cat "$ENGINE/.upstream_commit")"
if [ ${#conflicts[@]} -gt 0 ]; then
  echo "locally patched files kept (compare with upstream and re-apply if upstream changed them):"
  printf '  %s\n' "${conflicts[@]}"
fi
