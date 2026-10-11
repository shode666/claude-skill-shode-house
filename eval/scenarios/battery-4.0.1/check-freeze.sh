#!/usr/bin/env bash
# 4.0.1 routing-probe battery (P01..P47 mapped to the 6 types) -- its own manifest, independent of eval/FREEZE.sha256,
# eval/scenarios/core-4.0/FREEZE.sha256 and eval/shape-baseline/FREEZE.sha256. Those are the historical baseline and are never edited;
# this battery is DERIVED from the frozen eval/scenarios/golden.json by the one stated rule below, and the check re-derives it every time.
#   bash eval/scenarios/battery-4.0.1/check-freeze.sh            verify manifest + derivation (exit 0 = OK)
#   bash eval/scenarios/battery-4.0.1/check-freeze.sh --update   re-derive battery-4.0.1.json and rewrite the manifest
#                                                               (a new revision of this battery: disclose it; only before a run)
# Rule: copy every `kind: probe` scenario of golden.json in order (same id, prompt file, max_turns, class, desc, source, fixture_flags,
# related, not_applicable, and every expected field except the agent ids). In `expected.route_any` (agent:<id>) and
# `expected.must_not_dispatch` rewrite each 4.0.0 agent id to its 4.0.1 type (TYPE below; the 7 domain ids and the `*-expert` glob -> plan;
# `orchestrator` is the router itself, not a spawn type, and is dropped). A list keeps its order and loses duplicates. A type that the
# probe REQUIRES (route_any) is removed from its must_not_dispatch (two 4.0.0 ids that are now one type cannot be required and forbidden
# at once); the removed names are recorded in `dropped_4_0_1`. Added per probe: `type_4_0_1` (first required type, or "-" for a
# skill-only route), `mode_4_0_1` (MODE below: the mode or review axis that owns it) and, for the 7 single-domain probes,
# `domain_4_0_1` (scored by check-domain.py: the plan spawn names that domain's reference and the pinned model tier). The sha256 of the
# source is recorded in the battery and must match. Prompts (eval/prompts/probes/*.md) are the baseline's, pinned by eval/FREEZE.sha256.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="${FREEZE_ROOT:-$(cd "$HERE/../../.." && pwd -P)}"
exec python3 - "$ROOT" "$HERE" "${1:-}" <<'PY'
import copy, fnmatch, hashlib, json, os, sys
root, here, mode = sys.argv[1], sys.argv[2], sys.argv[3]
SOURCE = "eval/scenarios/golden.json"
SET, MANIFEST = os.path.join(here, "battery-4.0.1.json"), os.path.join(here, "FREEZE.sha256")
FILES = ["eval/scenarios/battery-4.0.1/battery-4.0.1.json", "eval/scenarios/battery-4.0.1/README.md",
         "eval/scenarios/battery-4.0.1/check-freeze.sh", "eval/scenarios/battery-4.0.1/check-domain.py",
         "eval/run-battery-4.0.1.sh"]
DOMAINS = ("fintech", "erp", "sap", "trading", "insurance", "booking", "ecommerce")
TYPE = {"product-manager": "plan", "business-analyst": "plan", "solution-architect": "plan", "developer": "build",
        "staff-engineer": "build", "code-reviewer": "verify", "qa-engineer": "verify", "security-engineer": "secure",
        "ux-ui-designer": "design", "devops-engineer": "operate", "sre-engineer": "operate", "*-expert": "plan"}
for d in DOMAINS:
    TYPE[d + "-expert"] = "plan"
DROP = {"orchestrator"}
DOMAIN_TIER = {"opus": ["fintech", "sap", "trading", "insurance"], "default": ["erp", "booking", "ecommerce"]}
DOMAIN_PROBE = {"P15": "fintech", "P23": "trading", "P24": "insurance", "P42": "erp", "P43": "sap", "P44": "booking", "P45": "ecommerce"}
MODE = {
    "P01": "build: implement a small behaviour test-first (skill dev-gate)", "P02": "skill diagnose (bug root cause); no operate spawn",
    "P03": "operate, reliability mode (incident); not build", "P04": "skill data-migration", "P05": "plan, architecture mode (interface contract)",
    "P06": "secure (threat model)", "P07": "verify, runtime axis (UI end-to-end)", "P08": "plan, requirements mode (decompose)",
    "P09": "skill drain", "P10": "skill ask (team entry); no router spawn", "P11": "operate, reliability mode (SLO)",
    "P12": "design (web quality / Core Web Vitals)", "P13": "verify, runtime axis (test automation)", "P14": "verify, standards axis (review entry)",
    "P15": "plan, domain mode (fintech ledger rule)", "P16": "negative: plain SQL query, no spawn, no data-migration",
    "P17": "negative: private function, build alone", "P18": "negative: local refactor, build alone, no secure",
    "P19": "negative: backend-only test, verify (standards) or automate-test, no ui-test", "P20": "negative: variable named payment, build alone, no plan",
    "P21": "not applicable (style skill caveman)", "P22": "negative: smalltalk, no spawn",
    "P23": "plan, domain mode (trading matching engine)", "P24": "plan, domain mode (insurance policy admin)", "P25": "design (checkout UX)",
    "P26": "operate, deploy mode (Docker/CI)", "P27": "verify, standards axis (unit-test review)", "P28": "skill diagnose (paraphrase); no operate spawn",
    "P29": "operate, reliability mode (live customer impact)", "P30": "build: one small clear behaviour (paraphrase)",
    "P31": "skill data-migration or plan, domain mode (fintech) for a live 40M-row change", "P32": "plan, architecture mode (consumed field rename)",
    "P33": "secure (internal capability opened to outsiders)", "P34": "verify, runtime axis (repeatable UI check)", "P35": "operate, reliability mode (error budget)",
    "P36": "plan, requirements mode (decompose an agreed scope)", "P37": "negative: rename a variable, build alone, no plan",
    "P38": "negative: the word production in a README note, no operate", "P39": "negative: a wording comprehension test, no build or verify",
    "P40": "plan, discover mode (is it worth building, priority)", "P41": "build, staff-grade brief (error-handling convention, radar, refactor strategy)",
    "P42": "plan, domain mode (erp period-close)", "P43": "plan, domain mode (sap Z table vs append)", "P44": "plan, domain mode (booking allotment)",
    "P45": "plan, domain mode (ecommerce promotion stacking)", "P46": "negative: one-line message fix pitched as top priority, build alone",
    "P47": "negative: renaming a constant framed as project-wide consistency, build alone"}
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def to_type(name):
    return None if name in DROP else TYPE.get(name, name)


def derive():
    src = json.load(open(os.path.join(root, SOURCE), encoding="utf-8"))["scenarios"]
    out = []
    for s in src:
        if s.get("kind") != "probe":
            continue
        s = copy.deepcopy(s)
        exp = s.get("expected", {})
        required = []
        if "route_any" in exp:
            routes = []
            for r in exp["route_any"]:
                if r.startswith("agent:"):
                    t = to_type(r[6:])
                    r = "agent:" + t
                    required.append(t)
                if r not in routes:
                    routes.append(r)
            exp["route_any"] = routes
        dropped = []
        if "must_not_dispatch" in exp:
            kept = []
            for n in exp["must_not_dispatch"]:
                t = to_type(n)
                if t is None:
                    dropped.append(f"{n}: not a spawn type")
                elif t in required:
                    dropped.append(f"{n}: same type as the required route ({t})")
                elif t not in kept:
                    kept.append(t)
            exp["must_not_dispatch"] = kept
        if dropped:
            s["dropped_4_0_1"] = dropped
        s["type_4_0_1"] = next((r[6:] for r in exp.get("route_any", []) if r.startswith("agent:")), "-")
        s["mode_4_0_1"] = MODE[s["id"]]
        if s["id"] in DOMAIN_PROBE:
            s["domain_4_0_1"] = DOMAIN_PROBE[s["id"]]
        out.append(s)
    return {"_comment": "4.0.1 routing-probe battery: P01..P47 mapped to the 6 types, derived (see README.md); frozen by FREEZE.sha256 in this directory.",
            "derived_from": {SOURCE: sha(os.path.join(root, SOURCE))}, "domain_tier": DOMAIN_TIER, "scenarios": out}


if mode == "--update":
    with open(SET, "w", encoding="utf-8") as fh:
        json.dump(derive(), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        fh.write("".join("%s  %s\n" % (sha(os.path.join(root, f)), f) for f in FILES))
    print("battery-4.0.1 rewritten: %d probes, manifest %d files" % (len(derive()["scenarios"]), len(FILES)))
    sys.exit(0)
bad = []
try:
    want = dict(reversed(l.rstrip("\n").split("  ", 1)) for l in open(MANIFEST, encoding="utf-8") if l.strip())
except OSError:
    sys.exit("battery-4.0.1: FREEZE.sha256 missing")
for f in FILES:
    p = os.path.join(root, f)
    if f not in want:
        bad.append("UNLISTED " + f)
    elif not os.path.isfile(p):
        bad.append("MISSING " + f)
    elif sha(p) != want[f]:
        bad.append("CHANGED " + f)
bad += ["UNLISTED " + f for f in want if f not in FILES]
if not bad and json.load(open(SET, encoding="utf-8")) != derive():
    bad.append("DERIVATION battery-4.0.1.json is not the stated rule applied to the frozen golden.json")
print("\n".join(bad) if bad else "battery-4.0.1 freeze OK: %d files, derivation OK" % len(FILES))
sys.exit(1 if bad else 0)
PY
