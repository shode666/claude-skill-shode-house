#!/usr/bin/env bash
# 4.0.1 core scenario set (E01..E15, E10b, E1c; E16..E20 + the pre-registered probes beside it) for the 6-type roster -- its own manifest, independent of
# eval/FREEZE.sha256 and of eval/scenarios/core-4.0/FREEZE.sha256. Both older sets are pinned and never edited; this set
# is DERIVED from the frozen 4.0 set by one stated rule and the check below re-derives it every time.
#   bash eval/scenarios/core-4.0.1/check-freeze.sh            verify manifest + derivation (exit 0 = OK)
#   bash eval/scenarios/core-4.0.1/check-freeze.sh --update   re-derive core-4.0.1.json and rewrite the manifest
#                                                            (a new revision of this set: disclose it)
# Rule: copy every scenario of core-4.0.json in order; in `expected.agents`, `expected.must_not_dispatch`,
# `expected.first_action` and `expected.route_any` (agent:<id>) rewrite each retired 4.0.0 agent id to its 4.0.1 type (the 7 domain ids and
# the `*-expert` glob -> plan; business-analyst/product-manager/solution-architect -> plan; developer -> build;
# code-reviewer/qa-engineer -> verify; security-engineer -> secure; ux-ui-designer -> design). staff-engineer is DROPPED
# from a must_not_dispatch list (the staff-grade brief is `build`, which the implementer legitimately is). A list keeps
# its order and loses duplicates; a list that held only dropped ids stays []. A scenario that lost a staff-engineer entry
# gains `post_checks: ["no-fable-dispatch"]` (scored by check-probes.py; the old negative, restated for the build tier).
# Prompts, fixtures and every other field are unchanged. routing-4.0.1.json, probes-4.0.1.json (the pre-registered
# E19/E20 thresholds), check-probes.py and the E19 and E20 prompt files (eval/prompts/, the E20 one carries the closed-form contract the
# scorer reads) are pinned in the same manifest. The sha256 of the source set is recorded in the set and must match.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="${FREEZE_ROOT:-$(cd "$HERE/../../.." && pwd -P)}"
exec python3 - "$ROOT" "$HERE" "${1:-}" <<'PY'
import copy, hashlib, json, os, sys
root, here, mode = sys.argv[1], sys.argv[2], sys.argv[3]
SOURCE = "eval/scenarios/core-4.0/core-4.0.json"
SET, MANIFEST = os.path.join(here, "core-4.0.1.json"), os.path.join(here, "FREEZE.sha256")
FILES = ["core-4.0.1.json", "routing-4.0.1.json", "probes-4.0.1.json", "check-probes.py", "README.md", "check-freeze.sh",
         "../../prompts/E19-served-model-override.md", "../../prompts/E20-spec-axis-seeded-violations.md"]
TYPE = {"product-manager": "plan", "business-analyst": "plan", "solution-architect": "plan", "developer": "build",
        "code-reviewer": "verify", "qa-engineer": "verify", "security-engineer": "secure", "ux-ui-designer": "design",
        "devops-engineer": "operate", "sre-engineer": "operate", "*-expert": "plan"}
for d in ("fintech", "erp", "sap", "trading", "insurance", "booking", "ecommerce"):
    TYPE[d + "-expert"] = "plan"
DROP = {"staff-engineer"}
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def mapped(names, dropping):
    out = []
    for n in names:
        if n in DROP and dropping:
            continue
        n = TYPE.get(n, n)
        if n not in out:
            out.append(n)
    return out


def derive():
    src = json.load(open(os.path.join(root, SOURCE), encoding="utf-8"))["scenarios"]
    out = []
    for s in src:
        s = copy.deepcopy(s)
        exp = s.get("expected", {})
        if "agents" in exp:
            exp["agents"] = mapped(exp["agents"], False)
        if "must_not_dispatch" in exp:
            if any(n in DROP for n in exp["must_not_dispatch"]):
                # the dropped staff-engineer negative (no over-dispatch of the staff-grade tier on ordinary work) lives on as
                # a post_check scored by check-probes.py: no main-session fable request, no fable model in modelUsage
                s["post_checks"] = ["no-fable-dispatch"]
            exp["must_not_dispatch"] = mapped(exp["must_not_dispatch"], True)
        fa = exp.get("first_action", "")
        if fa.startswith("agent:"):
            exp["first_action"] = "agent:" + mapped([fa[6:]], False)[0]
        if "route_any" in exp:
            exp["route_any"] = [("agent:" + mapped([r[6:]], False)[0]) if r.startswith("agent:") else r for r in exp["route_any"]]
        out.append(s)
    return {"_comment": "4.0.1 core scenarios for the 6-type roster, derived (see README.md); frozen by FREEZE.sha256 in this directory.",
            "derived_from": {SOURCE: sha(os.path.join(root, SOURCE))}, "scenarios": out}


if mode == "--update":
    with open(SET, "w", encoding="utf-8") as fh:
        json.dump(derive(), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        fh.write("".join("%s  %s\n" % (sha(os.path.join(here, f)), f) for f in FILES))
    print("core-4.0.1 rewritten: %d scenarios, manifest %d files" % (len(derive()["scenarios"]), len(FILES)))
    sys.exit(0)
bad = []
try:
    want = dict(reversed(l.rstrip("\n").split("  ", 1)) for l in open(MANIFEST, encoding="utf-8") if l.strip())
except OSError:
    sys.exit("core-4.0.1: FREEZE.sha256 missing")
for f in FILES:
    p = os.path.join(here, f)
    if f not in want:
        bad.append("UNLISTED " + f)
    elif not os.path.isfile(p):
        bad.append("MISSING " + f)
    elif sha(p) != want[f]:
        bad.append("CHANGED " + f)
if not bad and json.load(open(SET, encoding="utf-8")) != derive():
    bad.append("DERIVATION core-4.0.1.json is not the stated rule applied to the frozen 4.0 set")
print("\n".join(bad) if bad else "core-4.0.1 freeze OK: %d files, derivation OK" % len(FILES))
sys.exit(1 if bad else 0)
PY
