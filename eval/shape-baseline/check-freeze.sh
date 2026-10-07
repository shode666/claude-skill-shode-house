#!/usr/bin/env bash
# Verifies eval/shape-baseline against its own manifest (independent of eval/FREEZE.sha256).
#   bash eval/shape-baseline/check-freeze.sh           # exit 0 = identical
#   bash eval/shape-baseline/check-freeze.sh --update  # rewrite the manifest (a NEW protocol revision; disclose it)
set -u
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 3
FILES="protocol.md REVISIONS.md scenarios.json role-map.3.17.2.json role-policy.json lib.sh control.sh run.sh matrix.sh fixture.sh hook-snap.py metrics.py score.py scrub.py summarize.py check-freeze.sh acceptance/test_bd106.py overlays/S3/outputs/SPEC-bd-106.md"
if [ "${1:-}" = --update ]; then
  # shellcheck disable=SC2086
  shasum -a 256 $FILES | grep -v ' check-freeze.sh$' > FREEZE.sha256; echo "manifest rewritten: $(wc -l < FREEZE.sha256) files"; exit 0
fi
[ -f FREEZE.sha256 ] || { echo "shape-baseline: no FREEZE.sha256" >&2; exit 1; }
out="$(shasum -a 256 -c FREEZE.sha256 2>&1)"; rc=$?
if [ $rc -eq 0 ]; then echo "shape-baseline freeze OK: $(wc -l < FREEZE.sha256 | tr -d ' ') files"
else printf '%s\n' "$out" | grep -v ': OK$'; echo "shape-baseline freeze MISMATCH" >&2; fi
exit $rc
