#!/usr/bin/env python3
"""A1 (v4 ADR §6 / SAC-5): per-type `tools:` pin -- the host-enforced boundary of each agent type.

`tools:` is the one per-type control the host enforces (ADR §5.1), so a change to it must be a
reviewed change to this pin, never a side effect of a body edit. The agent set is read from
agents/*.md, never from a count: every agent file must have a pin and every pin a file.

Two pins, selected by DATA (ADR §7 W1/W10 -- the 4.0.0 switch flips them, nobody edits a flag):
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
PIN_4X = {k: set(v) for k, v in PIN_3X.items() if k != "orchestrator"}
PIN_4X["ux-ui-designer"] = PIN_3X["ux-ui-designer"] - {B}   # UD R16: design scripts run in a separate spawn
NEVER_4X = {"Task", "Agent"}                                   # ADR §5.2: no type spawns another

# What the 4.0.0 pin reports on the 3.17.2 tree -- the reason A1-4x is wired, not yet required (ADR §7 W1).
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
            self.assertEqual([], found, "pin = 4.0.0")
        elif found:
            self.skipTest(f"A1 tree check advisory until 4.0.0 (ADR §7 W1), {len(found)} finding(s): " + " | ".join(found))

    def test_agent_set_is_read_from_files(self):
        self.assertTrue(self.tools)
        self.assertEqual({p.stem for p in (ROOT / "agents").glob("*.md")}, set(self.tools))

    # --- mutations (ADR A1: "mutation adds Bash to business-analyst -> red"), under both pins ---
    def test_bash_added_to_business_analyst_is_red(self):
        for pin in (PIN_3X, PIN_4X):
            errs = self.errors_with("business-analyst", list(pin["business-analyst"]) + [B], pin)
            self.assertIn("business-analyst: tools: has Bash, not in the pin", errs)

    def test_skill_removed_is_red(self):
        tools = [t for t in self.tools["developer"] if t != SK]
        self.assertIn("developer: tools: lacks Skill, which the pin requires", self.errors_with("developer", tools))

    def test_unpinned_new_agent_is_red(self):
        self.assertIn("new-role: agent file has no pin (new or retired type? update the pin in a reviewed change)",
                      self.errors_with("new-role", [R, SK]))

    def test_deleted_pinned_agent_is_red(self):
        mutated = {k: v for k, v in self.tools.items() if k != "erp-expert"}
        pin = active()[0]
        self.assertIn("erp-expert: pinned type has no agents/erp-expert.md", pin_errors(mutated, pin))

    def test_omitted_or_malformed_tools_is_red(self):
        for bad in ("no `tools:` line (an omitted tools: inherits every tool)", "tools: is not a one-line JSON array of strings"):
            self.assertIn("developer: " + bad, self.errors_with("developer", bad))

    def test_duplicate_tool_is_red(self):
        self.assertIn("developer: tools: lists a tool twice",
                      self.errors_with("developer", list(self.tools["developer"]) + [R]))

    def test_v4_forbids_task_and_agent_everywhere(self):
        for t in sorted(NEVER_4X):
            errs = self.errors_with("developer", sorted(PIN_4X["developer"]) + [t], PIN_4X, NEVER_4X)
            self.assertIn(f"developer: tools: has {t}, which no 4.0.0 type may hold", errs)

    def test_v4_pin_is_3x_minus_the_planned_changes_only(self):
        no_bash_3x = {k for k, v in PIN_3X.items() if B not in v}
        no_bash_4x = {k for k, v in PIN_4X.items() if B not in v}
        self.assertEqual(no_bash_3x | {"ux-ui-designer"}, no_bash_4x)    # ADR §5.2: no-Bash set grows by ux only
        self.assertEqual(set(PIN_3X) - {"orchestrator"}, set(PIN_4X))
        self.assertEqual({k: v for k, v in PIN_3X.items() if k not in ("orchestrator", "ux-ui-designer")},
                         {k: v for k, v in PIN_4X.items() if k != "ux-ui-designer"})
        self.assertFalse(any(NEVER_4X & v for v in PIN_4X.values()))

    def test_v4_pin_on_today_tree_reports_only_the_planned_switch(self):
        """Required ratchet while the tree check is advisory: only the planned 4.0.0 changes may differ."""
        if v4_required():
            self.skipTest("4.0.0 pin is the active pin; covered by test_tree_matches_active_pin")
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

    def test_duplicate_tools_key_on_a_pinned_agent_breaks_the_ratchet(self):
        """F5 mutation on a real 4.0.0 type: its pinned `tools:` line + a second `tools: [... Task ...]` must not stay
        green. Re-targeted from agents/orchestrator.md (retired in 4.0.0; the router is an output style with no
        `tools:` key, so it has no pin to break) to agents/developer.md, so the check runs instead of skipping."""
        text = (ROOT / "agents/developer.md").read_text()
        line = next(l for l in text.splitlines() if l.startswith("tools:"))
        mutated = text.replace(line, line + '\ntools: ["Read", "Task", "Skill"]', 1)
        self.assertNotEqual(text, mutated)
        tools = dict(self.tools, developer=parse_tools(mutated))
        self.assertFalse(set(pin_errors(tools, PIN_4X, NEVER_4X)) <= EXPECTED_3X_GAP)
        self.assertIn("developer: tools key appears 2 times (duplicate or variant spelling: a host may read either one)",
                      pin_errors(tools, PIN_4X, NEVER_4X))
        self.assertIn("developer: tools key appears 2 times (duplicate or variant spelling: a host may read either one)",
                      pin_errors(tools, PIN_3X))

    def test_parameterised_spawn_tool_is_red_in_4x_and_breaks_the_ratchet(self):
        for spawn in ("Agent(worker)", "Task(*)", "Task(code-reviewer)"):
            with self.subTest(spawn=spawn):
                errs = self.errors_with("developer", sorted(PIN_4X["developer"]) + [spawn], PIN_4X, NEVER_4X)
                self.assertIn(f"developer: tools: has {spawn}, which no 4.0.0 type may hold", errs)
                router = dict(self.tools, orchestrator=sorted(PIN_3X["orchestrator"] - {T}) + [spawn])
                self.assertFalse(set(pin_errors(router, PIN_4X, NEVER_4X)) <= EXPECTED_3X_GAP)

    def test_ratchet_catches_unplanned_drift_and_passes_the_staged_ux_change(self):
        """G2: W5a's staged ux-without-Bash stays green; Bash added to business-analyst stays red."""
        staged = dict(self.tools, **{"ux-ui-designer": sorted(PIN_4X["ux-ui-designer"])})
        self.assertTrue(set(pin_errors(staged, PIN_4X, NEVER_4X)) <= EXPECTED_3X_GAP)
        drift = dict(self.tools, **{"business-analyst": sorted(PIN_3X["business-analyst"] | {B})})
        self.assertFalse(set(pin_errors(drift, PIN_4X, NEVER_4X)) <= EXPECTED_3X_GAP)

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
