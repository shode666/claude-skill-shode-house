"""W9 (task shode-house-v7u.4.20): role-map.4.0.0-C.json (ADR iter 5 section 6, protocol section 9 step 2) and the
frozen 4.0 core scenario set eval/scenarios/core-4.0/ (review finding N2, 06-chris-w3-review-r2.md)."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SB = ROOT / "eval" / "shape-baseline"
sys.path.insert(0, str(ROOT / "eval" / "v4-security"))
import v4_rules  # noqa: E402

ORDER = v4_rules.ORDER_NAME_PATTERN
RETIRED = "orch" + "estrator"
ROSTER_4_0 = {"product-manager", "business-analyst", "ux-ui-designer", "solution-architect", "staff-engineer",
              "security-engineer", "developer", "code-reviewer", "qa-engineer", "devops-engineer", "sre-engineer",
              "fintech-expert", "trading-expert", "insurance-expert", "sap-expert", "erp-expert", "booking-expert",
              "ecommerce-expert"}


def load(p):
    return json.load(open(p, encoding="utf-8"))


def test_role_map_is_the_baseline_map_minus_the_retired_type():
    base, new = load(SB / "role-map.3.17.2.json"), load(SB / "role-map.4.0.0-C.json")
    assert new["arm"] == "4.0.0-C"
    want = {k: v for k, v in base["types"].items() if k != RETIRED}
    assert new["types"] == want
    assert set(new["types"]) == ROSTER_4_0                       # ADR section 5.2: 18 types
    for key in ("namespace", "host_builtin_types", "host_builtin_role"):
        assert new[key] == base[key], key
    assert base["rules"] == []
    # S-1 / R71: the only addition is the design-run executor rules (protocol section 9 step 2 allows `rules`)
    assert new["rules"] == [{"type": "qa-engineer", "prompt_regex": ORDER, "roles": ["review-runtime"]},
                            {"type": "developer", "prompt_regex": ORDER, "roles": ["implementer"]}]
    assert RETIRED not in json.dumps(new)


def test_every_role_has_a_policy_and_router_stays_unmapped():
    new, policy = load(SB / "role-map.4.0.0-C.json"), load(SB / "role-policy.json")
    roles = {r for rs in new["types"].values() for r in rs}
    assert roles <= set(policy["roles"])
    assert "router" not in roles


def test_role_map_through_the_frozen_role_of():
    spec = importlib.util.spec_from_file_location("frozen_metrics", SB / "metrics.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    rm = load(SB / "role-map.4.0.0-C.json")
    assert m.role_of("shode-house:developer", "", rm) == ["implementer"]
    assert m.role_of("shode-house:qa-engineer", "router: shode-house@4.0.0 task:t phase:3a iter:1", rm) == ["review-runtime", "ui-verify"]
    assert m.role_of("shode-house:" + RETIRED, "", rm) == ["unmapped"]
    assert m.role_of("developer", "", rm) == ["unmapped"]          # a bare-name spawn is not the arm's agent (H1)
    assert m.role_of("Explore", "", rm) == ["host-builtin"]


def test_shape_baseline_freeze_untouched():
    r = subprocess.run(["bash", str(SB / "check-freeze.sh")], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "role-map.4.0.0-C.json" not in (SB / "FREEZE.sha256").read_text()


def test_probe_freeze_untouched():
    r = subprocess.run(["bash", str(ROOT / "eval" / "check-freeze.sh")], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert r.returncode == 0 and r.stdout.startswith(b"freeze OK"), r.stdout + r.stderr


def test_core_4_0_freeze_and_derivation():
    r = subprocess.run(["bash", str(ROOT / "eval/scenarios/core-4.0/check-freeze.sh")], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    assert r.returncode == 0, r.stdout + r.stderr
    assert b"derivation OK" in r.stdout


def test_core_4_0_differs_from_3_17_only_by_the_retired_type(tmp_path):
    golden = load(ROOT / "eval/scenarios/golden.json")["scenarios"]
    core = load(ROOT / "eval/scenarios/core-3.17.json")["scenarios"]
    old = [s for s in golden if s.get("kind") == "core"] + core
    new = load(ROOT / "eval/scenarios/core-4.0/core-4.0.json")["scenarios"]
    assert [s["id"] for s in new] == [s["id"] for s in old] and len(new) == 17
    for a, b in zip(old, new):
        a = json.loads(json.dumps(a))
        if "must_not_dispatch" in a["expected"]:
            assert RETIRED in a["expected"]["must_not_dispatch"]
            a["expected"]["must_not_dispatch"].remove(RETIRED)
        assert a == b, a["id"]
    assert RETIRED not in json.dumps(new)


def test_core_4_0_check_detects_a_hand_edit(tmp_path):
    import shutil
    dst = tmp_path / "repo"
    for rel in ("eval/scenarios/golden.json", "eval/scenarios/core-3.17.json", "eval/scenarios/core-4.0"):
        src = ROOT / rel
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if src.is_dir() else shutil.copy)(src, dst / rel)
    p = dst / "eval/scenarios/core-4.0/core-4.0.json"
    data = load(p)
    data["scenarios"][0]["expected"]["max_spawns"] = 9
    p.write_text(json.dumps(data, indent=1) + "\n")
    env = {"FREEZE_ROOT": str(dst), "PATH": "/usr/bin:/bin"}
    r = subprocess.run(["bash", str(dst / "eval/scenarios/core-4.0/check-freeze.sh")], env=env, stdout=subprocess.PIPE)
    assert r.returncode == 1 and b"CHANGED core-4.0.json" in r.stdout
    # re-hashing the manifest does not hide it: the derivation check still fails
    import hashlib
    man = dst / "eval/scenarios/core-4.0/FREEZE.sha256"
    lines = [l for l in man.read_text().splitlines() if not l.endswith("  core-4.0.json")]
    lines.append("%s  core-4.0.json" % hashlib.sha256(p.read_bytes()).hexdigest())
    man.write_text("\n".join(lines) + "\n")
    r = subprocess.run(["bash", str(dst / "eval/scenarios/core-4.0/check-freeze.sh")], env=env, stdout=subprocess.PIPE)
    assert r.returncode == 1 and b"DERIVATION" in r.stdout


# ---- Bella W9 S-1 / S-3, router decision R71 ----------------------------------------------------------------------
HDR = "router: shode-house@4.0.0 task:t-1 phase:3a iter:1"
EXEC_QA = HDR + "\nDesign run 3a: order outputs/t-1/02-design-run-order-3a-iter1.json sha256 " + "a" * 64 + "."
EXEC_DEV = HDR + "\nDesign run 1b: order outputs/t-1/02-design-run-order-1b-iter1.json sha256 " + "a" * 64 + "."
REVIEW_QA = HDR + ("\nUI verification of the checkout change. Design-run report (relayed): "
                   "outputs/t-1/design-run/02-design-run-order-3a-iter1.report.json sha256 " + "b" * 64 + ".")


def frozen_metrics():
    spec = importlib.util.spec_from_file_location("frozen_metrics", SB / "metrics.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_executor_rules_through_the_frozen_role_of():
    m, rm = frozen_metrics(), load(SB / "role-map.4.0.0-C.json")
    assert m.role_of("shode-house:qa-engineer", EXEC_QA, rm) == ["review-runtime"]          # never ui-verify
    assert m.role_of("shode-house:developer", EXEC_DEV, rm) == ["implementer"]
    assert m.role_of("shode-house:qa-engineer", REVIEW_QA, rm) == ["review-runtime", "ui-verify"]   # S-2 report path
    assert m.role_of("shode-house:qa-engineer", HDR + "\nRuntime review.", rm) == ["review-runtime", "ui-verify"]
    assert m.role_of("shode-house:ux-ui-designer", EXEC_QA, rm) == ["ux-design", "ui-verify"]       # rules are per type
    assert v4_rules.ORDER_IN_TEXT_RE.pattern == ORDER                                              # one definition


def _s4_boundary(role_map, spawns):
    """The three S4 boundary checks of the frozen score.py (roles_required, separate_spawns,
    review_after_last_source_edit) computed the way score.py computes them (`have`, t0 vs the last source edit),
    with roles from the frozen metrics.role_of and the boundary block from the frozen scenarios.json."""
    m = frozen_metrics()
    b = next(s for s in load(SB / "scenarios.json")["scenarios"] if s["id"] == "S4")["boundary"]
    have = {}
    for sp in spawns:
        sp = dict(sp, roles=m.role_of(sp["type"], sp["prompt"], role_map))
        for r in sp["roles"]:
            have.setdefault(r, []).append(sp)
    last_edit = max(sp["edit_ts"] for sp in spawns if sp.get("edit_ts"))
    out = {}
    for r in b["roles_required"]:
        out["required:" + r] = bool(have.get(r))
    for x, y in b["separate_spawns"]:
        out["separate:%s/%s" % (x, y)] = any(a["id"] != c["id"] for a in have.get(x, []) for c in have.get(y, []))
    for r in b["review_after_last_source_edit"]:
        out["after:" + r] = any(sp["t0"] > last_edit for sp in have.get(r, []))
    return out


IMPL = {"id": "agent-impl", "type": "shode-house:developer", "prompt": HDR + "\nImplement the 180-day filter.",
        "t0": "2026-10-04T00:00:01Z", "edit_ts": "2026-10-04T00:00:05Z"}
EXEC = {"id": "agent-exec", "type": "shode-house:qa-engineer", "prompt": EXEC_QA, "t0": "2026-10-04T00:00:09Z"}
UIREV = {"id": "agent-ui", "type": "shode-house:qa-engineer", "prompt": REVIEW_QA, "t0": "2026-10-04T00:00:12Z"}


def test_s4_cannot_be_satisfied_by_a_design_run_executor_spawn():
    """S-1 must-fail: implementer + a 3a executor started after the last edit, no UI verifier -> S4 boundary fails."""
    got = _s4_boundary(load(SB / "role-map.4.0.0-C.json"), [IMPL, EXEC])
    assert got["required:ui-verify"] is False and got["after:ui-verify"] is False
    assert got["separate:implementer/ui-verify"] is False


def test_s4_is_satisfied_by_a_real_ui_verifier_also_when_it_gets_the_report_path():
    """S-1 / S-2 must-pass control: a qa UI verifier handed the relayed report path still counts as ui-verify."""
    got = _s4_boundary(load(SB / "role-map.4.0.0-C.json"), [IMPL, EXEC, UIREV])
    assert all(got.values()), got


def test_mutation_map_without_executor_rules_lets_the_executor_satisfy_s4():
    """Removing the S-1 rules (the iter-2 map) lets the executor spawn satisfy all three S4 checks."""
    rm = dict(load(SB / "role-map.4.0.0-C.json"), rules=[])
    got = _s4_boundary(rm, [IMPL, EXEC])
    assert all(got.values()), got


def test_mutation_iter2_order_regex_makes_the_report_reviewer_an_executor():
    """S-2 mutation: with the iter-2 unanchored regex as the rule, the relayed report path matches and the UI
    verifier loses ui-verify, so S4 would fail on a correct run."""
    old = r"outputs/[A-Za-z0-9._/-]*design-run-order-[A-Za-z0-9._-]+\.json"
    rm = load(SB / "role-map.4.0.0-C.json")
    rm = dict(rm, rules=[dict(r, prompt_regex=old) for r in rm["rules"]])
    got = _s4_boundary(rm, [IMPL, EXEC, UIREV])
    assert got["required:ui-verify"] is False


def test_c_s_reuses_the_c_map_and_run_sh_records_it():
    """S-3 / R71: arm 4.0.0-C-S reuses the C map. The frozen run.sh hashes role-map.<arm>.json into meta.json;
    the C-S file is a byte-equal copy, so meta.json records sha256["role-map.4.0.0-C-S.json"] == the C map's."""
    import hashlib
    c, cs = SB / "role-map.4.0.0-C.json", SB / "role-map.4.0.0-C-S.json"
    assert c.read_bytes() == cs.read_bytes()
    run_sh = (SB / "run.sh").read_text()
    assert '"role-map.%s.json" % e["M_ARM"]' in run_sh                    # the frozen key run.sh writes
    key = "role-map.%s.json" % "4.0.0-C-S"
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest() if p.exists() else None   # run.sh's sha()
    assert sha(SB / key) == sha(c) is not None
    assert "4.0.0-C-S" in load(c)["note"] and "byte-equal" in load(c)["note"]
