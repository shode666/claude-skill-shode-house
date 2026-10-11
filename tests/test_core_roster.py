#!/usr/bin/env python3
"""4.0.1 core-agent gates: the roster is the 6 approved types and routing, review independence, tool/model
boundaries, the floor and the hook keys still hold after the 18 -> 6 consolidation (outputs/v4-core-reduce/,
router decisions R93, security acceptance SEC-1..SEC-12, requirements AC-1..AC-11).

What this file proves (each is a gate, none is a count that can drift quietly):
  roster      agents/*.md == APPROVED exactly (a diff is printed), file name == frontmatter name, nothing listed in a
              manifest that is not a file, no retired id (tests/test_tombstone.py holds the spawn-form scan)
  models      frontmatter model: `claude-fable-5` on `secure` and `design` only (SEC-4), sonnet elsewhere
  floor       scripts/floor.py --check --require is green over the 6 bodies + the router style (AC-4)
  registries  tool-profiles / delegation / capabilities / routes name only live types (SEC-9); `operate` carries its
              recorded _widening (SEC-5); permission-check.sh answers UNKNOWN (exit 2) for each retired id (SEC-7)
  routing     every row of tests/fixtures/routing_inventory.json (the 4.0.0 router table + the non-table capabilities)
              maps to a live type in the shipped text (AC-2.1)
  review card six axis lines, `verify` on standards + runtime and `plan` on spec + domain as separate named spawns,
              spec never SKIP, no line merges two axes (AC-3.1, SEC-8)
  hook keys   every agent_type value a hook branches on is listed once and is a live type; the ux path set DENIES a
              `shode-house:design` write outside outputs/ and design-system/ (SEC-1/SEC-2); a stale constant is shown
              to switch the control off, so the test can fail
  dispatch    Phase 1c -> secure, business rule -> domain-loaded plan before any implementer, served-model evidence and
              no-bare-fallback sentences are in the router style (SEC-3, SEC-6, SEC-11)
Run: python3 tests/test_core_roster.py            (CI gate #27 loop, make validate; also collected by pytest)
     python3 tests/test_core_roster.py --scan     failing test ids; exit 1 when any
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APPROVED = ("build", "design", "operate", "plan", "secure", "verify")
FABLE_PINNED = {"secure", "design"}
DOMAINS = ("fintech", "erp", "sap", "trading", "insurance", "booking", "ecommerce")
RETIRED_4_0_0 = ("product-manager", "business-analyst", "solution-architect", "staff-engineer", "developer",
                 "ux-ui-designer", "code-reviewer", "qa-engineer", "security-engineer", "devops-engineer", "sre-engineer",
                 "fintech-expert", "erp-expert", "sap-expert", "trading-expert", "insurance-expert", "booking-expert",
                 "ecommerce-expert")
STYLE = ROOT / "output-styles/shode-house.md"
GUARD = ROOT / "hooks/scripts/guard-scope-write.sh"


def fm(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return {}
    out = {}
    for line in lines[1:lines.index("---", 1)]:
        m = re.match(r"([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def agents():
    return {p.stem: p.read_text() for p in sorted((ROOT / "agents").glob("*.md"))}


def style_section(name, end=None):
    text = STYLE.read_text()
    start = text.index(name)
    stop = text.index(end, start + 1) if end else len(text)
    return text[start:stop]


def routing_rows():
    """{outcome: type cell} from the router style's `Outcome|type (mode)` table."""
    sec = style_section("## Routing", "## Dispatch floor")
    rows = {}
    for line in sec.splitlines():
        if line.count("|") == 1 and not line.startswith(("Outcome", "---")):
            k, v = line.split("|")
            rows[k.strip()] = v.strip()
    return rows


def card_lines():
    sec = style_section("## Review card", "## Spawns")
    return [l for l in sec.splitlines() if l.startswith("- axis=")]


class RosterTest(unittest.TestCase):
    def test_roster_is_exactly_the_approved_six(self):
        have = sorted(agents())
        self.assertEqual(sorted(APPROVED), have, f"agents/ diff: extra {sorted(set(have) - set(APPROVED))}, "
                                                 f"missing {sorted(set(APPROVED) - set(have))}")
        self.assertEqual(6, len(have))
        self.assertTrue(4 <= len(have) <= 6)            # AC-1.1
        for name, text in agents().items():
            self.assertEqual(name, fm(text).get("name"), f"agents/{name}.md frontmatter name")
            self.assertTrue(fm(text).get("description"), f"agents/{name}.md description")

    def test_no_stub_for_a_retired_id_and_manifests_name_no_phantom(self):
        for old in RETIRED_4_0_0:
            self.assertFalse((ROOT / "agents" / f"{old}.md").exists(), old)
        for mf in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
            data = json.loads((ROOT / mf).read_text())
            listed = list(data.get("agents", [])) + [a for p in data.get("plugins", []) for a in p.get("agents", [])]
            for path in listed:
                self.assertTrue((ROOT / path).is_file(), f"{mf} lists a phantom agent {path}")
                self.assertIn(pathlib.PurePosixPath(path).stem, APPROVED)

    def test_every_body_has_bias_discipline_skill_tool_and_at_most_three_skills(self):
        for name, text in agents().items():
            meta = fm(text)
            self.assertRegex(text, r"(?m)^## .*Bias Discipline", name)
            self.assertIn('"Skill"', meta["tools"], f"{name}: Skill in tools")
            skills = json.loads(meta["skills"])
            self.assertLessEqual(len(skills), 3)
            self.assertIn("shode-house:shode-house-discipline", skills)

    def test_models_fable_only_on_secure_and_design(self):
        for name, text in agents().items():
            model = fm(text)["model"]
            self.assertEqual("claude-fable-5" if name in FABLE_PINNED else "sonnet", model, name)

    def test_manifest_and_budget_files_follow_the_roster(self):
        for bf in (".preload-budget", ".agent-core-budget"):
            keys = {l.split("=")[0] for l in (ROOT / bf).read_text().splitlines() if l and not l.startswith("#")}
            self.assertEqual(set(APPROVED), keys, bf)
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        descs = [plugin["description"], market["description"]] + [p["description"] for p in market["plugins"]]
        for d in descs:
            self.assertNotRegex(d, r"\b18\b", d)
        self.assertRegex(plugin["description"], r"\b6 agent")
        self.assertEqual(plugin["version"], market["plugins"][0]["version"])

    def test_ci_model_whitelist_is_exactly_the_two_host_pinned_types(self):
        """SEC-4: CI #5's claude-fable-5 allow-list is secure + design and nothing else."""
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertRegex(ci, r'(?m)^\s+F5="secure design"')
        self.assertEqual(sorted(FABLE_PINNED), sorted(re.search(r'F5="([^"]+)"', ci).group(1).split()))

    def test_domain_content_is_reference_not_skill_or_agent(self):
        skills = [p for b in ("workflow", "ops", "ui", "style", "discipline") for p in (ROOT / "skills" / b).glob("*/SKILL.md")]
        self.assertEqual(20, len(skills), "no 21st skill (R93)")
        core = (ROOT / "skills/discipline/domain-core/SKILL.md").read_text()
        for d in DOMAINS:
            ref = ROOT / "references/domain" / f"{d}.md"
            self.assertTrue(ref.is_file(), ref)
            text = ref.read_text()
            self.assertRegex(text, rf"(?m)^LOAD: references/domain/{d}\.md$")
            self.assertRegex(text, r"(?m)^OWNER: plan$")
            self.assertIn(f"references/domain/{d}.md", core, f"domain-core must list {d}")
        self.assertEqual(sorted(DOMAINS), sorted(p.stem for p in (ROOT / "references/domain").glob("*.md")))


class FloorTest(unittest.TestCase):
    def test_floor_in_every_body_and_the_style(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/floor.py"), "--check", "--require", "--root", str(ROOT)],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        floor = (ROOT / ".safety-floor/body.md").read_text()
        for name, text in agents().items():
            self.assertIn(floor, text, f"{name}: floor block")


class RegistryTest(unittest.TestCase):
    def load(self, rel):
        return json.loads((ROOT / rel).read_text())

    def test_tool_profiles_match_frontmatter_verbatim_and_the_roster(self):
        prof = self.load("references/security/tool-profiles.json")["profiles"]
        self.assertEqual(sorted(APPROVED), sorted(prof))
        for name, text in agents().items():
            self.assertEqual(json.loads(fm(text)["tools"]), prof[name]["tools"], name)
            self.assertEqual(f"agents/{name}.md", prof[name]["source"])
            self.assertFalse(prof[name]["tool_grants"]["spawn"])

    def test_operate_policy_union_is_a_recorded_widening(self):
        """SEC-5: one operate profile grants deploy/deploy_prod/write_code to every brief; the delta is written down."""
        op = self.load("references/security/tool-profiles.json")["profiles"]["operate"]
        self.assertEqual({"write_code": True, "deploy": True, "deploy_prod": True}, op["policy"])
        w = op["_widening"]
        for word in ("sre-engineer", "deploy_prod", "write_code", "reason"):
            self.assertIn(word, json.dumps(w))
        body = agents()["operate"]
        for sentence in ("recorded widening", "pre-deploy-*", "R0"):
            self.assertIn(sentence, body)
        self.assertIn("_widening", self.load("references/security/tool-profiles.json")["profiles"]["build"])

    def test_operate_reliability_brief_uses_deploy_or_prod_only_when_the_delegation_explicitly_authorises_it(self):
        """U30 SEC-5 condition: the one operate policy is not a grant to a reliability (SRE) brief."""
        body = " ".join(agents()["operate"].split())
        self.assertIn("A reliability (SRE) brief may therefore use deploy, prod or product-code actions only when its delegation "
                      "explicitly authorises that action; the `pre-deploy-*` gates and the R0 floor line apply unchanged.", body)
        # the audit record of the widening says the same thing as the body (Standards F4, Spec S-11): "explicitly authorises", not "names"
        reason = self.load("references/security/tool-profiles.json")["profiles"]["operate"]["_widening"]["reason"]
        self.assertIn("only when its delegation explicitly authorises that action", reason)
        self.assertNotIn("delegation names", reason)
        # the pre-deploy gates and R0 text this condition leans on are still the router's: never skipped, R0 needs the quoted confirmation
        style = " ".join(STYLE.read_text().split())
        self.assertIn("`pre-deploy-*`", style)
        self.assertIn("Delegating an R0 action: quote the user's confirmation of that exact action", style)
        # both recorded widenings stay: operate (deploy, deploy_prod, write_code) and build (write_code)
        prof = self.load("references/security/tool-profiles.json")["profiles"]
        self.assertIn("_widening", prof["operate"])
        self.assertIn("_widening", prof["build"])
        self.assertEqual({"write_code": True, "deploy": True, "deploy_prod": True}, prof["operate"]["policy"])

    def test_delegation_spawns_nothing(self):
        d = self.load("references/security/delegation.json")
        self.assertEqual(sorted(APPROVED), sorted(d["delegation"]))
        self.assertTrue(all(v["can_spawn"] == [] for v in d["delegation"].values()))
        self.assertEqual(1, d["max_depth"])

    def test_capabilities_and_routes_name_only_live_owners(self):
        def live(ident):
            base, _, dom = ident.partition(":")
            self.assertIn(base, APPROVED, ident)
            if dom:
                self.assertEqual("plan", base, ident)
                self.assertTrue((ROOT / "references/domain" / f"{dom}.md").is_file(), ident)
        caps = self.load("references/registry/capabilities.json")["capabilities"]
        self.assertEqual(18, len(caps))
        for cap in caps.values():
            live(cap["owner"])
        routes = self.load("references/registry/routes.json")["routes"]
        for r in routes:
            self.assertTrue(r["require"], r["id"])
            for ident in r["require"]:
                live(ident)

    def test_permission_check_answers_unknown_for_every_retired_id(self):
        script = ROOT / "scripts/permission-check.sh"
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / ".shode-house").mkdir()        # no engagement dir = guard off (exit 0, no output)
            env = {**os.environ, "PERMCHECK_ROOT": d}
            for old in RETIRED_4_0_0:
                r = subprocess.run(["bash", str(script), old, "write_files"], cwd=ROOT, capture_output=True, text=True, env=env)
                self.assertEqual(2, r.returncode, f"{old}: {r.stdout}{r.stderr}")
                self.assertTrue(r.stdout.startswith("UNKNOWN"), r.stdout)
                self.assertNotIn("18 registered", r.stdout)
                self.assertIn("Formerly", r.stdout)
            for live in APPROVED:       # the roster is allowed, so UNKNOWN above is the retirement and not a broken script
                r = subprocess.run(["bash", str(script), live, "write_files"], cwd=ROOT, capture_output=True, text=True, env=env)
                self.assertEqual(0, r.returncode, f"{live}: {r.stdout}{r.stderr}")


class RoutingTest(unittest.TestCase):
    inv = json.loads((ROOT / "tests/fixtures/routing_inventory.json").read_text())

    def test_inventory_types_are_the_roster(self):
        self.assertEqual(sorted(APPROVED), sorted(self.inv["types"]))
        ids = [r["id"] for r in self.inv["rows"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(sum(1 for r in self.inv["rows"] if r["kind"] == "route"), 18)

    def test_every_inventory_row_is_reachable_on_a_live_type(self):
        rows, card = routing_rows(), card_lines()
        for r in self.inv["rows"]:
            with self.subTest(row=r["id"]):
                self.assertIn(r["type"], APPROVED)
                if r["kind"] == "route":
                    self.assertIn(r["outcome"], rows, "outcome row missing from the router Routing table (orphaned)")
                    self.assertIn(f"`{r['type']}`", rows[r["outcome"]])
                    if "domain" in r:
                        self.assertIn(f"`{r['domain']}`", rows[r["outcome"]])
                        self.assertTrue((ROOT / "references/domain" / f"{r['domain']}.md").is_file())
                elif r["kind"] == "axis":
                    line = [l for l in card if l.startswith(f"- axis={r['axis']}:")]
                    self.assertEqual(1, len(line), r["axis"])
                    self.assertIn(f"`shode-house:{r['type']}`", line[0])
                else:
                    text = " ".join((ROOT / r["file"]).read_text().split())
                    self.assertIn(" ".join(r["literal"].split()), text, f"{r['file']}")

    def test_domain_outcomes_each_name_their_own_reference(self):
        rows = routing_rows()
        refs = [re.search(r"domain `(\w+)`", v).group(1) for k, v in rows.items() if "domain `" in v]
        self.assertEqual(sorted(DOMAINS), sorted(refs))

    def test_no_routing_row_names_a_retired_id(self):
        for k, v in routing_rows().items():
            self.assertFalse(any(old in v for old in RETIRED_4_0_0), (k, v))
            self.assertTrue(re.search(r"`(%s)`" % "|".join(APPROVED), v), (k, v))


class ReviewCardTest(unittest.TestCase):
    def test_six_separate_axes_on_live_types(self):
        card = card_lines()
        self.assertEqual(["standards", "spec", "runtime", "security", "domain", "ui"],
                         [re.match(r"- axis=(\w+):", l).group(1) for l in card])
        want = {"standards": "verify", "spec": "plan", "runtime": "verify", "security": "secure", "domain": "plan", "ui": "design"}
        for l in card:
            axis = re.match(r"- axis=(\w+):", l).group(1)
            self.assertEqual(1, l.count("axis="), "a card line must not merge two axes")
            self.assertEqual([want[axis]], re.findall(r"`shode-house:(\w+)`", l), l)

    def test_shared_types_are_distinct_named_spawns(self):
        card = {re.match(r"- axis=(\w+):", l).group(1): l for l in card_lines()}
        names = {a: re.search(r"name: ([\w-]+)", l).group(1) for a, l in card.items() if "name:" in l}
        for a in ("standards", "spec", "runtime", "domain"):
            self.assertIn(a, names, f"{a} needs a name: label")
        self.assertNotEqual(names["standards"], names["runtime"])      # verify serves both
        self.assertNotEqual(names["spec"], names["domain"])            # plan serves both
        self.assertEqual(4, len(set(names.values())))

    def test_spec_never_skip_and_independence_sentences(self):
        card = {re.match(r"- axis=(\w+):", l).group(1): l for l in card_lines()}
        for axis in ("standards", "spec"):
            self.assertNotIn('SKIP("', card[axis], f"{axis} never offers SKIP")
        self.assertIn("always; no SKIP", card["spec"])
        self.assertIn("never the spawn that wrote or amended the AC", card["spec"])
        sec = style_section("## Review card", "## Spawns")
        for sentence in ("One fresh spawn per axis, one axis per spawn", "never merge or rerank across axes",
                         "never a producer's PASS/done claim", "`BLOCKED: no-spec`"):
            self.assertIn(sentence, sec)
        self.assertIn("BLOCKED: one-axis-per-spawn", agents()["verify"])

    def test_independence_line_is_in_every_reviewing_body(self):
        line = "never open another axis's report, a sibling verdict or the implementer's PASS/done claims"
        for name in ("plan", "verify", "secure", "design"):
            self.assertIn(line, agents()[name], name)


class DispatchTest(unittest.TestCase):
    def test_router_sentences_for_sec_3_6_11(self):
        style = " ".join(STYLE.read_text().split())
        for sentence in (
            "A failed `shode-house:<id>` spawn is never retried as a bare type",
            "skills/discipline/shode-house-routing/ownership.md` § Formerly",
            "Every override dispatch and every `shode-house:secure` dispatch records requested and served model in the returned artifact",
            "is BLOCKED, never PASS",
            "dispatch `shode-house:secure` now, before Phase 2",
            "never offer a skip or implement-in-parallel option",
            "wait for its return before any implementer",
            "`model: \"opus\"`", "`model: \"fable\"`",
        ):
            self.assertIn(sentence, style)

    def test_override_bodies_record_requested_and_served_model(self):
        for name in ("plan", "build"):
            self.assertRegex(agents()[name], r"model your (own )?system prompt says serves you", name)


class DomainTierTest(unittest.TestCase):
    """U30: opus for fintech, sap, trading, insurance (the 4.0.0 mapping); erp, booking, ecommerce default to the type (sonnet)
    and get an opus override only for high-stakes work, the reason recorded in the dispatch. Not one tier for all seven."""
    OPUS = ("fintech", "sap", "trading", "insurance")
    DEFAULT = ("erp", "booking", "ecommerce")

    def test_the_two_groups_cover_the_seven_domains(self):
        self.assertEqual(sorted(DOMAINS), sorted(self.OPUS + self.DEFAULT))

    def test_router_style_states_the_split_and_the_recorded_reason(self):
        style = " ".join(STYLE.read_text().split())
        self.assertIn('domain briefs `model: "opus"` for fintech, sap, trading, insurance, and for erp, booking, ecommerce only when '
                      "high-stakes, the reason in the dispatch (else the type default)", style)

    def test_ownership_rows_carry_the_per_domain_model(self):
        text = (ROOT / "skills/discipline/shode-house-routing/ownership.md").read_text()
        for d in self.OPUS:
            self.assertRegex(text, rf'`plan` \+ `references/domain/{d}\.md`, `model: "opus"` \|', d)
        for d in self.DEFAULT:
            self.assertRegex(text, rf"`plan` \+ `references/domain/{d}\.md`, type default \(sonnet\), `opus` if high-stakes \|", d)
        self.assertIn("the reason recorded in the dispatch", " ".join(text.split()))

    def test_plan_body_domain_core_and_review_command_agree(self):
        plan = " ".join(agents()["plan"].split())
        self.assertIn("`model: opus` on fintech, sap, trading, insurance briefs (erp, booking, ecommerce: type default, `opus` only if "
                      "high-stakes, reason recorded)", plan)
        core = " ".join((ROOT / "skills/discipline/domain-core/SKILL.md").read_text().split())
        self.assertIn("`opus` for fintech, sap, trading, insurance; erp, booking, ecommerce at the type default unless the dispatch "
                      "records a high-stakes reason for `opus`", core)
        review = (ROOT / "commands/review.md").read_text()
        self.assertNotIn('`model: "opus"` (name: plan-domain)', review)

    def test_no_shipped_or_maintainer_text_says_one_opus_tier_for_all_seven(self):
        for rel in ("README.md", "CHANGELOG.md", "output-styles/shode-house.md", "agents/plan.md", "commands/review.md",
                    "skills/discipline/domain-core/SKILL.md", "skills/discipline/shode-house-routing/ownership.md"):
            text = " ".join((ROOT / rel).read_text().split())
            self.assertNotRegex(text, r"(?i)one tier (\(`?opus`?\) )?for all seven|opus for all (7|seven)", rel)
            self.assertNotRegex(text, r"erp, booking and ecommerce were sonnet in 4\.0\.0\.\s*$", rel)

    def test_e19_still_targets_an_opus_domain(self):
        prompt = (ROOT / "eval/prompts/E19-served-model-override.md").read_text()
        self.assertIn("fintech reference", prompt)
        probe = json.loads((ROOT / "eval/scenarios/core-4.0.1/probes-4.0.1.json").read_text())["probes"]["E19"]
        self.assertEqual(("plan", "opus"), (probe["override_type"], probe["override_model"]))
        self.assertIn("fintech", self.OPUS)


class BuildPreloadTest(unittest.TestCase):
    """Standards F2 / F6: `build` is the main code producer, so the deliverable contract is host-injected (preloaded) like
    the developer's, not a load-before-return sentence; its body meets the strictest replaced key (staff-engineer)."""
    def skills_of(self, name):
        return re.findall(r"shode-house:([\w-]+)", re.search(r"(?m)^skills:\s*(.*)$", agents()[name]).group(1))

    def test_build_preloads_discipline_and_deliverable(self):
        self.assertEqual(["shode-house-discipline", "shode-house-deliverable"], self.skills_of("build"))
        self.assertEqual(self.skills_of("plan"), self.skills_of("build"))

    def test_no_load_before_return_substitute_in_the_body(self):
        body = agents()["build"].split("---", 2)[2]
        self.assertNotRegex(body, r"(?i)before every return load|it is not preloaded")

    def test_preload_key_is_the_measured_value_and_not_above_the_developer_key(self):
        keys = dict(l.split("=") for l in (ROOT / ".preload-budget").read_text().splitlines() if "=" in l and not l.startswith("#"))
        def size(n):
            return next(p for g in ("discipline", "workflow", "ops", "ui", "style") for p in [ROOT / "skills" / g / n / "SKILL.md"] if p.is_file()).stat().st_size
        measured = sum(size(n) for n in self.skills_of("build"))
        self.assertEqual(measured, int(keys["build"]))
        self.assertLessEqual(measured, 13310)          # the developer key (4.0.0), the role whose preload build keeps

    def test_core_body_meets_the_strictest_replaced_key_and_has_one_pre_edit_gate(self):
        keys = dict(l.split("=") for l in (ROOT / ".agent-core-budget").read_text().splitlines() if "=" in l and not l.startswith("#"))
        self.assertLessEqual(int(keys["build"]), 6441)                   # staff-engineer 4.0.0
        self.assertLessEqual((ROOT / "agents/build.md").stat().st_size, int(keys["build"]))
        text = agents()["build"]
        self.assertEqual(1, len(re.findall(r"BLOCKED: no-threat-model", text)))
        self.assertIn("IAM, secrets, session, PII, money, network exposure, CI/deploy permissions, an external integration, a webhook, file upload or an AI agent", text)


class HookKeyTest(unittest.TestCase):
    """SEC-1 / SEC-2: the ux path set is keyed on agent_type; a rename must turn CI red, never switch the control off."""
    def branch_list(self):
        text = GUARD.read_text()
        listed = re.findall(r"(?m)^#\s+agent-type-branch:\s+(shode-house:[a-z-]+)\s*$", text)
        const = re.search(r'(?m)^UX_AGENT_TYPE="([^"]+)"$', text).group(1)
        return listed, const, text

    def test_every_branch_value_is_a_live_type_and_listed_once(self):
        listed, const, text = self.branch_list()
        self.assertEqual(["shode-house:design"], listed)
        self.assertEqual(listed[0], const, "UX_AGENT_TYPE must equal the listed ux entry")
        for value in listed:
            self.assertIn(value.split(":", 1)[1], APPROVED)
            self.assertTrue((ROOT / "agents" / f"{value.split(':', 1)[1]}.md").is_file())
        # no other `shode-house:<id>` literal is compared against an agent_type / subagent_type anywhere in the hooks or scripts
        self.assertEqual([], self.stale_literals(ROOT / "hooks/scripts", ROOT / "scripts"))

    @staticmethod
    def stale_literals(*dirs):
        """agent_type lines naming a non-live `shode-house:<id>`; regular files only (a __pycache__ dir is not a script)."""
        bad = []
        for d in dirs:
            for p in sorted(q for q in pathlib.Path(d).glob("*") if q.is_file()):
                try:
                    lines = p.read_text().splitlines()
                except UnicodeDecodeError:
                    continue            # a compiled .pyc is not script text
                for line in lines:
                    if re.search(r"agent_type|AGENT_TYPE|subagent_type", line):
                        for ident in re.findall(r"shode-house:([a-z][a-z-]*)", line):
                            if ident not in APPROVED:
                                bad.append(f"{p.name}: {line.strip()[:100]}")
        return bad

    def test_scan_skips_directories_and_still_flags_a_stale_id(self):
        with tempfile.TemporaryDirectory() as d:
            hs = pathlib.Path(d) / "hooks/scripts"
            (hs / "__pycache__").mkdir(parents=True)
            (hs / "__pycache__" / "x.pyc").write_bytes(b"\xff\xfe\x00")
            (hs / "ok.sh").write_text('[ "$agent_type" = "shode-house:design" ]\n')
            self.assertEqual([], self.stale_literals(hs))
            (hs / "bad.sh").write_text('[ "$agent_type" = "shode-house:ux-ui-designer" ]\n')
            self.assertEqual(1, len(self.stale_literals(hs)))

    def run_guard(self, guard, project, agent_type, rel):
        payload = json.dumps({"tool_name": "Write", "agent_id": "agent-t", "agent_type": agent_type,
                              "tool_input": {"file_path": str(project / rel)}})
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
        r = subprocess.run(["bash", str(guard)], input=payload, cwd=project, env=env, capture_output=True, text=True)
        return r.returncode, r.stderr

    def test_design_write_outside_outputs_is_denied_and_a_stale_constant_is_not(self):
        with tempfile.TemporaryDirectory() as d:
            proj = pathlib.Path(d) / "proj"
            (proj / "src").mkdir(parents=True)
            rc, err = self.run_guard(GUARD, proj, "shode-house:design", "src/x.ts")
            self.assertEqual(2, rc, err)
            self.assertIn("ux-path-outside", err)
            rc, err = self.run_guard(GUARD, proj, "shode-house:design", "outputs/t/01-design.md")
            self.assertEqual(0, rc, err)
            rc, err = self.run_guard(GUARD, proj, "shode-house:build", "src/x.ts")
            self.assertEqual(0, rc, err)       # the ux set applies to the designer only
            # the test can fail: a guard whose constant names a retired id lets the same write through
            hooks = pathlib.Path(d) / "hooks"
            shutil.copytree(ROOT / "hooks", hooks)
            stale = hooks / "scripts/guard-scope-write.sh"
            stale.write_text(stale.read_text().replace('UX_AGENT_TYPE="shode-house:design"', 'UX_AGENT_TYPE="shode-house:ux-ui-designer"'))
            rc, err = self.run_guard(stale, proj, "shode-house:design", "src/x.ts")
            self.assertEqual(0, rc, "a stale constant must be visibly broken: the control is off")


if __name__ == "__main__":
    if "--scan" in sys.argv:
        suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
        result = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
        for t, _ in result.failures + result.errors:
            print(t.id())
        sys.exit(0 if result.wasSuccessful() else 1)
    unittest.main()
