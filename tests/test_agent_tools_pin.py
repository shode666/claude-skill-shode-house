#!/usr/bin/env python3
"""A1 (v4 ADR §6 / SAC-5): per-type `tools:` pin -- the host-enforced boundary of each agent type.

`tools:` is the one per-type control the host enforces (ADR §5.1), so a change to it must be a
reviewed change to this pin, never a side effect of a body edit. The agent set is read from
agents/*.md, never from a count: every agent file must have a pin and every pin a file.

v4.0.1: the roster is 6 types (plan build verify operate secure design); PIN_4X below is their pin and PIN_4_0_0 the
retired 18-id roster whose per-role tools are the ceilings. Two pins, selected by DATA (ADR §7 W1/W10 -- the 4.0.0 switch flips them, nobody edits a flag):
  PIN_3X  = today's tools (3.17.x), the active pin while .claude-plugin/plugin.json major < 4.
  PIN_4X  = ADR §5.2 roster: `orchestrator` retired, `ux-ui-designer` without Bash, no type holds
            `Task` or `Agent`. Active from 4.0.0, or now with SHODE_REQUIRE_V4=1 (rehearsal).
Required vs advisory (ADR iter 5 §7 W1 "A1 pin ... wired but not yet required"; router decision G2):
  - the unit + mutation tests always run and are required;
  - the TREE check against the active pin is advisory while REQ4=0 (a skip naming every finding), so a
    staged S2 worktree (W5a: ux without Bash) can stay green; it is required from 4.0.0;
  - the ratchet test is required now: the 4.0.0 pin may report nothing on the tree beyond EXPECTED_3X_GAP,
    so any tools drift other than the planned switch (e.g. Bash added to business-analyst) is red today.
Run: python3 tests/test_agent_tools_pin.py           unit + mutation tests (CI gate #27)
     python3 tests/test_agent_tools_pin.py --scan    findings under the active pin (--v4: the 4.0.0 pin)
"""
import json
import os
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

R, W, E, G, GL, B, WS, WF, SK, T = ("Read", "Write", "Edit", "Grep", "Glob", "Bash", "WebSearch", "WebFetch",
                                    "Skill", "Task")
DOMAIN_FETCH = {R, W, E, G, GL, WS, WF, SK}
IMPLEMENT = {R, W, E, G, GL, B, SK}

PIN_3X = {
    "product-manager": {R, W, E, WS, WF, G, GL, SK},
    "business-analyst": {R, W, E, WS, G, GL, SK},
    "ux-ui-designer": {R, W, E, G, GL, B, WS, WF, SK},
    "solution-architect": {R, W, E, G, GL, WS, WF, SK},
    "staff-engineer": {R, G, GL, B, WS, W, E, SK},
    "security-engineer": {R, W, E, G, GL, B, WS, SK},
    "developer": IMPLEMENT,
    "code-reviewer": IMPLEMENT,
    "qa-engineer": IMPLEMENT,
    "devops-engineer": IMPLEMENT,
    "sre-engineer": IMPLEMENT,
    "fintech-expert": DOMAIN_FETCH,
    "trading-expert": DOMAIN_FETCH,
    "insurance-expert": DOMAIN_FETCH,
    "sap-expert": DOMAIN_FETCH,
    "booking-expert": DOMAIN_FETCH,
    "ecommerce-expert": DOMAIN_FETCH,
    "erp-expert": {R, W, E, G, GL, WS, SK},
    "orchestrator": {R, W, E, GL, G, T, B, SK},
}
# 4.0.0 roster (18 types), kept as DATA: the per-role ceilings the 4.0.1 types may not exceed (AC-5.1, tool ceilings per type)
PIN_4_0_0 = {k: set(v) for k, v in PIN_3X.items() if k != "orchestrator"}
PIN_4_0_0["ux-ui-designer"] = PIN_3X["ux-ui-designer"] - {B}   # UD R16: design scripts run in a separate spawn
# 4.0.1 roster: 6 agent types (outputs/v4-core-reduce/02-sara-adr.md §2, router decisions R93). One `tools:` allowlist per type.
PIN_4X = {
    "plan": {R, W, E, G, GL, WS, WF, SK},
    "build": IMPLEMENT,
    "verify": IMPLEMENT,
    "operate": IMPLEMENT,
    "secure": {R, W, E, G, GL, B, WS, SK},
    "design": {R, W, E, G, GL, WS, WF, SK},
}
# which 4.0.0 ids each 4.0.1 type absorbed: the tool ceiling of a type is the widest member, never the union with a wider type
MERGED_FROM = {
    "plan": ["product-manager", "business-analyst", "solution-architect", "fintech-expert", "erp-expert", "sap-expert",
             "trading-expert", "insurance-expert", "booking-expert", "ecommerce-expert"],
    "build": ["developer", "staff-engineer"], "verify": ["code-reviewer", "qa-engineer"],
    "operate": ["devops-engineer", "sre-engineer"], "secure": ["security-engineer"], "design": ["ux-ui-designer"],
}
NEVER_4X = {"Task", "Agent"}                                   # ADR §5.2: no type spawns another

# Historic (3.17.x -> 4.0.0 staging): what the 4.0.0 pin reported on the 3.17.2 tree. Kept for the staged-ratchet tests below,
# which only run while plugin.json major < 4 (never again on a 4.x tree).
EXPECTED_3X_GAP = {
    "ux-ui-designer: tools: has Bash, not in the pin",
    "orchestrator: agent file has no pin (new or retired type? update the pin in a reviewed change)",
    "orchestrator: tools: has Task, which no 4.0.0 type may hold",
}


def v4_required(root=ROOT):
    """Data switch shared by the v4 gates: plugin.json major >= 4, or SHODE_REQUIRE_V4=1."""
    if os.environ.get("SHODE_REQUIRE_V4") == "1":
        return True
    try:
        version = json.loads((root / ".claude-plugin/plugin.json").read_text())["version"]
        return int(str(version).split(".")[0]) >= 4
    except (OSError, ValueError, KeyError, TypeError):
        return False


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return None
    return lines[1:lines.index("---", 1)]


TOOLS_KEY = re.compile(r"""^\s*["']?tools["']?\s*:""")   # a tools key in any spelling (Sentinel W1 follow-up F5)


def parse_tools(text):
    """list-of-tools | error string for one agent file."""
    fm = frontmatter(text)
    keys = [l for l in fm or [] if TOOLS_KEY.match(l)]
    if len(keys) > 1:
        return f"tools key appears {len(keys)} times (duplicate or variant spelling: a host may read either one)"
    if keys and not keys[0].startswith("tools:"):
        return "tools key is not spelled `tools:` at column 0"
    line = keys[0] if keys else None
    if line is None:
        return "no `tools:` line (an omitted tools: inherits every tool)"
    try:
        tools = json.loads(line[len("tools:"):].strip())
    except ValueError:
        tools = None
    if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        return "tools: is not a one-line JSON array of strings"
    return tools


def read_tools(root=ROOT):
    """{agent: list-of-tools | error string} straight from agents/*.md."""
    return {p.stem: parse_tools(p.read_text()) for p in sorted((root / "agents").glob("*.md"))}


def pin_errors(tools_by_agent, pin, never=frozenset()):
    errors = []
    for name, tools in sorted(tools_by_agent.items()):
        if isinstance(tools, str):
            errors.append(f"{name}: {tools}")
            continue
        if len(tools) != len(set(tools)):
            errors.append(f"{name}: tools: lists a tool twice")
        # F5: a parameterised spawn form (`Agent(worker)`, `Task(*)`) is that spawn tool
        for t in sorted(t for t in set(tools) if t in never or t.startswith(tuple(f"{n}(" for n in never))):
            errors.append(f"{name}: tools: has {t}, which no 4.0.0 type may hold")
        if name not in pin:
            errors.append(f"{name}: agent file has no pin (new or retired type? update the pin in a reviewed change)")
            continue
        for t in sorted(set(tools) - pin[name]):
            errors.append(f"{name}: tools: has {t}, not in the pin")
        for t in sorted(pin[name] - set(tools)):
            errors.append(f"{name}: tools: lacks {t}, which the pin requires")
    for name in sorted(set(pin) - set(tools_by_agent)):
        errors.append(f"{name}: pinned type has no agents/{name}.md")
    return errors


def active(root=ROOT, force_v4=False):
    return (PIN_4X, NEVER_4X) if force_v4 or v4_required(root) else (PIN_3X, frozenset())


def scan(root=ROOT, force_v4=False):
    pin, never = active(root, force_v4)
    return pin_errors(read_tools(root), pin, never)


class AgentToolsPinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = read_tools()

    def errors_with(self, name, tools, pin=None, never=frozenset()):
        mutated = dict(self.tools)
        mutated[name] = tools
        return pin_errors(mutated, pin or active()[0], never or active()[1])

    def test_tree_matches_active_pin(self):
        found = scan()
        if v4_required():
            self.assertEqual([], found, "pin = 4.0.1 roster")
        elif found:
            self.skipTest(f"A1 tree check advisory until 4.0.0 (ADR §7 W1), {len(found)} finding(s): " + " | ".join(found))

    def test_agent_set_is_read_from_files(self):
        self.assertTrue(self.tools)
        self.assertEqual({p.stem for p in (ROOT / "agents").glob("*.md")}, set(self.tools))

    # --- mutations (ADR A1: "mutation adds Bash to plan -> red"), under the 4.0.1 pin and the 4.0.0 / 3.x data ---
    def test_bash_added_to_plan_is_red(self):
        errs = self.errors_with("plan", list(PIN_4X["plan"]) + [B], PIN_4X)
        self.assertIn("plan: tools: has Bash, not in the pin", errs)
        for pin in (PIN_3X, PIN_4_0_0):    # the retired role it came from (data): same mutation, same finding
            errs = self.errors_with("business-analyst", list(pin["business-analyst"]) + [B], pin)
            self.assertIn("business-analyst: tools: has Bash, not in the pin", errs)

    def test_skill_removed_is_red(self):
        tools = [t for t in self.tools["build"] if t != SK]
        self.assertIn("build: tools: lacks Skill, which the pin requires", self.errors_with("build", tools))

    def test_unpinned_new_agent_is_red(self):
        self.assertIn("new-role: agent file has no pin (new or retired type? update the pin in a reviewed change)",
                      self.errors_with("new-role", [R, SK]))

    def test_deleted_pinned_agent_is_red(self):
        mutated = {k: v for k, v in self.tools.items() if k != "design"}
        pin = active()[0]
        self.assertIn("design: pinned type has no agents/design.md", pin_errors(mutated, pin))

    def test_retired_id_with_a_file_is_red(self):
        """A retired 4.0.0 id coming back as an agent file has no pin (the tombstone test names the same ids)."""
        for old in sorted(PIN_4_0_0):
            with self.subTest(old=old):
                self.assertIn(f"{old}: agent file has no pin (new or retired type? update the pin in a reviewed change)",
                              self.errors_with(old, [R, SK], PIN_4X, NEVER_4X))

    def test_omitted_or_malformed_tools_is_red(self):
        for bad in ("no `tools:` line (an omitted tools: inherits every tool)", "tools: is not a one-line JSON array of strings"):
            self.assertIn("build: " + bad, self.errors_with("build", bad))

    def test_duplicate_tool_is_red(self):
        self.assertIn("build: tools: lists a tool twice",
                      self.errors_with("build", list(self.tools["build"]) + [R]))

    def test_v4_forbids_task_and_agent_everywhere(self):
        for t in sorted(NEVER_4X):
            errs = self.errors_with("build", sorted(PIN_4X["build"]) + [t], PIN_4X, NEVER_4X)
            self.assertIn(f"build: tools: has {t}, which no 4.0.0 type may hold", errs)

    # --- tool ceilings per type (AC-5.1 / AC-5.2 / AC-10.4): a merged type is no wider than its widest member ---
    def test_each_new_type_is_no_wider_than_its_widest_replaced_role(self):
        for new, members in MERGED_FROM.items():
            with self.subTest(type=new):
                self.assertTrue(any(PIN_4X[new] <= PIN_4_0_0[m] for m in members),
                                f"{new}: tools {sorted(PIN_4X[new])} exceed every replaced role {members}")
                self.assertTrue(PIN_4X[new] <= set().union(*(PIN_4_0_0[m] for m in members)))

    def test_every_retired_role_has_exactly_one_new_home(self):
        homes = [m for ms in MERGED_FROM.values() for m in ms]
        self.assertEqual(sorted(homes), sorted(PIN_4_0_0), "every 4.0.0 id lands in exactly one 4.0.1 type")
        self.assertEqual(set(MERGED_FROM), set(PIN_4X))

    def test_named_boundaries_of_the_six_types(self):
        self.assertNotIn(B, PIN_4X["plan"], "plan must not gain Bash")
        self.assertNotIn(B, PIN_4X["design"], "design keeps no Bash (UD R16)")
        for name in ("verify", "build", "operate"):
            self.assertFalse({WS, WF} & PIN_4X[name], f"{name} stays offline")
        self.assertFalse(any(NEVER_4X & v for v in PIN_4X.values()))
        self.assertTrue(all(SK in v for v in PIN_4X.values()))
        self.assertEqual({"plan", "build", "verify", "operate", "secure", "design"}, set(PIN_4X))

    def test_v4_pin_on_today_tree_reports_only_the_planned_switch(self):
        """Required ratchet while the tree check is advisory: only the planned 4.0.0 changes may differ."""
        if v4_required():
            self.skipTest("4.x pin is the active pin; covered by test_tree_matches_active_pin")
        self.assertTrue(set(scan(force_v4=True)) <= EXPECTED_3X_GAP, scan(force_v4=True))

    # --- Sentinel W1 follow-up F5: duplicate / variant tools key, parameterised spawn tools ---
    def test_duplicate_or_variant_tools_key_is_red(self):
        head, tail = "---\nname: x\n", "---\n# X\n"
        good = 'tools: ["Read", "Skill"]\n'
        self.assertEqual(["Read", "Skill"], parse_tools(head + good + tail))
        for extra in ('tools: ["Read", "Task", "Skill"]\n', '"tools": ["Task"]\n', "  tools: [\"Task\"]\n",
                      "tools : [\"Task\"]\n", "'tools': [\"Task\"]\n"):
            with self.subTest(extra=extra):
                self.assertIn("tools key appears 2 times", parse_tools(head + good + extra + tail))
        for variant in ('tools : ["Read"]\n', '"tools": ["Read"]\n', '  tools: ["Read"]\n'):
            with self.subTest(variant=variant):
                self.assertEqual("tools key is not spelled `tools:` at column 0", parse_tools(head + variant + tail))

    def test_duplicate_tools_key_on_a_pinned_agent_breaks_the_pin(self):
        """F5 mutation on a real 4.0.1 type: its pinned `tools:` line + a second `tools: [... Task ...]` must not stay
        green (the router is an output style with no `tools:` key, so it has no pin to break)."""
        text = (ROOT / "agents/build.md").read_text()
        line = next(l for l in text.splitlines() if l.startswith("tools:"))
        mutated = text.replace(line, line + '\ntools: ["Read", "Task", "Skill"]', 1)
        self.assertNotEqual(text, mutated)
        tools = dict(self.tools, build=parse_tools(mutated))
        self.assertIn("build: tools key appears 2 times (duplicate or variant spelling: a host may read either one)",
                      pin_errors(tools, PIN_4X, NEVER_4X))

    def test_parameterised_spawn_tool_is_red_in_4x(self):
        for spawn in ("Agent(worker)", "Task(*)", "Task(verify)"):
            with self.subTest(spawn=spawn):
                errs = self.errors_with("build", sorted(PIN_4X["build"]) + [spawn], PIN_4X, NEVER_4X)
                self.assertIn(f"build: tools: has {spawn}, which no 4.0.0 type may hold", errs)

    # --- historic staging ratchet (3.17.2 -> 4.0.0), run on DATA (the 3.17.2 roster), never on the live tree ---
    def test_staged_ratchet_on_the_3x_roster(self):
        tools_3x = {k: sorted(v) for k, v in PIN_3X.items()}
        staged = dict(tools_3x, **{"ux-ui-designer": sorted(PIN_4_0_0["ux-ui-designer"])})
        self.assertTrue(set(pin_errors(staged, PIN_4_0_0, NEVER_4X)) <= EXPECTED_3X_GAP)
        drift = dict(tools_3x, **{"business-analyst": sorted(PIN_3X["business-analyst"] | {B})})
        self.assertFalse(set(pin_errors(drift, PIN_4_0_0, NEVER_4X)) <= EXPECTED_3X_GAP)
        for spawn in ("Agent(worker)", "Task(*)", "Task(code-reviewer)"):
            router = dict(tools_3x, orchestrator=sorted(PIN_3X["orchestrator"] - {T}) + [spawn])
            self.assertFalse(set(pin_errors(router, PIN_4_0_0, NEVER_4X)) <= EXPECTED_3X_GAP)

    # --- Chris W10a-S1: the two `tools:` readers (this file's A1 parse_tools, rule-conservation's spawn_tools) agree ---
    TOOLS_CASES = ('tools: ["Read", "Skill"]\n', 'tools: ["Read", "Task", "Skill"]\n', 'tools: ["Agent(worker)"]\n',
                   'tools: ["Task(*)", "Read"]\n', 'tools: []\n', 'tools: Read, Task\n', 'tools: ["Read", 1]\n',
                   'tools: {"a": 1}\n', 'tools: "Read"\n', 'tools: ["Read"]\ntools: ["Task"]\n',
                   'tools: ["Read"]\n"tools": ["Task"]\n', 'tools: ["Read"]\n  tools: ["Task"]\n', 'tools : ["Read"]\n',
                   '"tools": ["Read"]\n', "'tools': [\"Read\"]\n", '  tools: ["Read"]\n', 'tools:\t["Read"]\n',
                   'tools: ["Read"] # c\n', 'toolsx: ["Task"]\n', '')

    def test_both_tools_readers_agree(self):
        """S1: one frontmatter, two readers -- parse_tools gives a list exactly when spawn_tools gives a set, and the set
        is the spawn subset of that list; with no tools key, A1 reports it and rule-conservation says NO_TOOLS."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("rc_s1", ROOT / "scripts/rule-conservation.py")
        rc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rc)
        self.assertEqual(TOOLS_KEY.pattern, rc.TOOLS_KEY.pattern)            # the same key grammar, both copies
        for fm in self.TOOLS_CASES:
            text = "---\nname: x\n" + fm + "---\n# X\n"
            with self.subTest(fm=fm):
                a1, spawn = parse_tools(text), rc.spawn_tools(text)
                self.assertEqual(isinstance(a1, list), isinstance(spawn, set), (a1, spawn))
                if isinstance(a1, list):
                    self.assertEqual({t for t in a1 if t in ("Task", "Agent") or t.startswith(("Task(", "Agent("))}, spawn)
                elif spawn != rc.NO_TOOLS:
                    self.assertIsNone(spawn)
                    self.assertNotEqual("no `tools:` line (an omitted tools: inherits every tool)", a1)
                else:
                    self.assertEqual("no `tools:` line (an omitted tools: inherits every tool)", a1)
        for text in ("# no frontmatter\n", "---\nname: x\n"):                  # both readers: unreadable
            self.assertIsInstance(parse_tools(text), str)
            self.assertIsNone(rc.spawn_tools(text))

if __name__ == "__main__":
    if "--scan" in sys.argv:
        found = scan(force_v4="--v4" in sys.argv)
        print("\n".join(found) if found else "ok tools pin")
        sys.exit(1 if found else 0)
    unittest.main()
