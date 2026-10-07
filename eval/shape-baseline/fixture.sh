#!/usr/bin/env bash
# Deterministic fixture for one scenario of protocol shape-baseline-v1.
#   bash eval/shape-baseline/fixture.sh <dest> <scenario-id> <fixture-src>
# <fixture-src> = clean export of commit 1bc8174 (the pinned fixture builder, identical for every arm; its two
# scripts are checked against the sha256 recorded in scenarios.json). Commit dates and the fixture's "today" are
# pinned, so the fixture HEAD is the same sha in every run and every arm.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DEST="${1:?dest}"; ID="${2:?scenario id}"; SRC="${3:?fixture source (clean export of 1bc8174)}"
eval "$(python3 - "$HERE/scenarios.json" "$ID" <<'PY'
import json, shlex, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
s = next(x for x in d["scenarios"] if x["id"] == sys.argv[2])
f = s["fixture"]
print("CORE_ID=" + shlex.quote(f["core_id"]))
print("FLAGS=" + shlex.quote(" ".join(f.get("flags", []))))
print("OVERLAY=" + shlex.quote(f.get("overlay") or ""))
print("PIN_DATE=" + shlex.quote(d["fixture_source"]["pinned_date"]))
for k, v in d["fixture_source"]["sha256"].items():
    print(f"EXPECT_{k.replace('-', '_').replace('.', '_')}=" + shlex.quote(v))
PY
)"
for f in eval-fixture.sh eval-fixture-core.sh; do
  want_var="EXPECT_$(printf '%s' "$f" | tr '.-' '__')"
  got="$(shasum -a 256 "$SRC/scripts/$f" | cut -d' ' -f1)"
  [ "$got" = "${!want_var}" ] || { echo "!! $SRC/scripts/$f sha256 $got != pinned ${!want_var}" >&2; exit 3; }
done
export GIT_AUTHOR_DATE="${PIN_DATE}T00:00:00Z" GIT_COMMITTER_DATE="${PIN_DATE}T00:00:00Z" FIXTURE_TODAY="$PIN_DATE"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
# shellcheck disable=SC2086
bash "$SRC/scripts/eval-fixture-core.sh" "$DEST" --scenario "$CORE_ID" --no-tracker --no-resolve $FLAGS
if [ -n "$OVERLAY" ]; then
  cp -R "$HERE/overlays/$OVERLAY/." "$DEST/"
  git -C "$DEST" add -A && git -C "$DEST" commit -qm "fixture(shape-baseline $ID): overlay $OVERLAY"
fi
git -C "$DEST" rev-parse HEAD
