#!/usr/bin/env bash
# Probe-protocol freeze: fails (exit 1) when any file listed in eval/FREEZE.sha256 changed, is missing,
# or when a probe prompt exists that the manifest does not list.
#   bash eval/check-freeze.sh            verify
#   bash eval/check-freeze.sh --update   rewrite the manifest (a deliberate act: after it, BOTH arms must be
#                                        re-scored from raw traces / re-recorded; commit it together with the change)
# FREEZE_ROOT overrides the repo root (tests).
ROOT="${FREEZE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
exec python3 - "$ROOT" "${1:-}" <<'PY'
import glob, hashlib, os, sys
root, mode = sys.argv[1], sys.argv[2]
manifest = os.path.join(root, "eval/FREEZE.sha256")
FIXED = ["eval/scenarios/golden.json", "eval/scenarios/core-3.17.json", "scripts/team-run-check.py", "scripts/eval-fixture.sh",
         "eval/run-lib.sh", "eval/run-probes.sh", "eval/probe-agg.py", "eval/check-freeze.sh", "eval/check-arm-diff.sh",
         "eval/PROBE-GATE.md", "eval/PROBE-GATE-floor.md", "eval/heldout-3.17.SHA256SUMS"]
files = FIXED + sorted(os.path.relpath(p, root) for p in glob.glob(os.path.join(root, "eval/prompts/probes/*.md")))
digest = lambda rel: hashlib.sha256(open(os.path.join(root, rel), "rb").read()).hexdigest()
if mode == "--update":
    with open(manifest, "w", encoding="utf-8") as f:
        f.write("".join(f"{digest(rel)}  {rel}\n" for rel in files))
    print(f"FREEZE.sha256 rewritten: {len(files)} files"); sys.exit(0)
try:
    want = dict(reversed(line.rstrip("\n").split("  ", 1)) for line in open(manifest, encoding="utf-8") if line.strip())
except OSError:
    sys.exit("check-freeze: eval/FREEZE.sha256 missing")
bad = [f"CHANGED {rel}" for rel in want if os.path.isfile(os.path.join(root, rel)) and digest(rel) != want[rel]]
bad += [f"MISSING {rel}" for rel in want if not os.path.isfile(os.path.join(root, rel))]
bad += [f"UNLISTED {rel}" for rel in files if rel not in want]
print("\n".join(bad) if bad else f"freeze OK: {len(want)} files")
sys.exit(1 if bad else 0)
PY
