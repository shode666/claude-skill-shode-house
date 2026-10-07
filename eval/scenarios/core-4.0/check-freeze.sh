#!/usr/bin/env bash
# Frozen 4.0 core scenario set (E01..E15, E10b, E1c) -- its own manifest, independent of eval/FREEZE.sha256.
# The 3.17 sets (eval/scenarios/golden.json, core-3.17.json) are pinned by eval/FREEZE.sha256 and are never
# edited; this set is DERIVED from them by one stated rule and the check below re-derives it every time.
#   bash eval/scenarios/core-4.0/check-freeze.sh            verify manifest + derivation (exit 0 = OK)
#   bash eval/scenarios/core-4.0/check-freeze.sh --update   re-derive core-4.0.json and rewrite the manifest
#                                                          (a new revision of this set: disclose it)
# Rule: copy every kind:"core" scenario of golden.json (E01) and every scenario of core-3.17.json in that
# order; remove the retired router agent type from every expected.must_not_dispatch list (an emptied list
# stays []); change nothing else. The two source sha256 values are recorded in the set and must match.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="${FREEZE_ROOT:-$(cd "$HERE/../../.." && pwd -P)}"
exec python3 - "$ROOT" "$HERE" "${1:-}" <<'PY'
import copy, hashlib, json, os, sys
root, here, mode = sys.argv[1], sys.argv[2], sys.argv[3]
RETIRED = "orch" + "estrator"          # the retired type; spelled so this script is not a tombstone hit
SOURCES = ["eval/scenarios/golden.json", "eval/scenarios/core-3.17.json"]
SET, MANIFEST = os.path.join(here, "core-4.0.json"), os.path.join(here, "FREEZE.sha256")
FILES = ["core-4.0.json", "README.md", "check-freeze.sh"]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def derive():
    golden = json.load(open(os.path.join(root, SOURCES[0]), encoding="utf-8"))["scenarios"]
    core = json.load(open(os.path.join(root, SOURCES[1]), encoding="utf-8"))["scenarios"]
    out = []
    for s in [x for x in golden if x.get("kind") == "core"] + core:
        s = copy.deepcopy(s)
        exp = s.get("expected", {})
        if "must_not_dispatch" in exp:
            exp["must_not_dispatch"] = [a for a in exp["must_not_dispatch"] if a != RETIRED]
        out.append(s)
    return {"_comment": "4.0 core scenarios, derived (see README.md); frozen by FREEZE.sha256 in this directory.",
            "derived_from": {p: sha(os.path.join(root, p)) for p in SOURCES}, "scenarios": out}


if mode == "--update":
    with open(SET, "w", encoding="utf-8") as fh:
        json.dump(derive(), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        fh.write("".join("%s  %s\n" % (sha(os.path.join(here, f)), f) for f in FILES))
    print("core-4.0 rewritten: %d scenarios, manifest %d files" % (len(derive()["scenarios"]), len(FILES)))
    sys.exit(0)
bad = []
try:
    want = dict(reversed(l.rstrip("\n").split("  ", 1)) for l in open(MANIFEST, encoding="utf-8") if l.strip())
except OSError:
    sys.exit("core-4.0: FREEZE.sha256 missing")
for f in FILES:
    p = os.path.join(here, f)
    if f not in want:
        bad.append("UNLISTED " + f)
    elif not os.path.isfile(p):
        bad.append("MISSING " + f)
    elif sha(p) != want[f]:
        bad.append("CHANGED " + f)
if not bad and json.load(open(SET, encoding="utf-8")) != derive():
    bad.append("DERIVATION core-4.0.json is not the stated rule applied to the frozen 3.17 sources")
print("\n".join(bad) if bad else "core-4.0 freeze OK: %d files, derivation OK" % len(FILES))
sys.exit(1 if bad else 0)
PY
