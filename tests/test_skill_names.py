#!/usr/bin/env python3
"""A8 (v4 ADR §6 / SAC-20, F-8b): skill names and spawn forms in shipped text.

A skill name that is not shipped is a pointer to nothing -- or to whatever project file of that name
shadows it (ADR §2 H2). A spawn by bare type name is served by a project agent, never the plugin body
(H1). Sets are read from the files: plugin name + shipped buckets from .claude-plugin/plugin.json,
skills = shipped SKILL.md dirs, agents/commands/styles from their dirs, shipped text from
.pack-allowlist (fallback: the manifest buckets + agents, commands, output-styles, references).

Reference forms recognised (documented limits -- a name in none of them is not seen):
  preload    `skills: [...]` in agents/*.md frontmatter, bare or `<plugin>:<name>`
  load       backticked names after a load verb (load/loads/invoke/invokes/Skill/โหลด) in the same clause,
             parenthesised asides removed first; the call form Skill(`<name>`) / Skill("<name>");
             "`<name>` skill" anywhere. Exempt: `formerly (the) ` directly before the name (history),
             lines carrying `tombstone-allow`
  namespaced `<plugin>:<name>` anywhere must name a shipped skill, agent, command or style
  spawn      in output-styles/, commands/, references/ and shipped skills (agents/ hold no spawn tool
             from 4.0.0, A1): a quoted or backticked agent type after spawn/dispatch/delegate/Agent(/Task(
             without the `<plugin>:` prefix, or a retired agent type (tests/test_team_package.py RETIRED)
             in that position with or without it; the key form `subagent_type:`/`agentType:` must name an
             existing agent (prefixed from 4.0.0 rules, bare is a finding) -- a non-agent name there is red.
Not seen (limits): a name only in a table cell or prose without a load verb; "`<name>` -> load it first"
(verb after the name); a spawn of an unquoted name ("dispatch developer"), of a persona name ("dispatch
Sentinel") or through a variable (`agentType: it.type`).
From 4.0.0 (plugin.json major >= 4, or SHODE_REQUIRE_V4=1) every preload and load must ALSO be
namespaced, and the check is REQUIRED. Before that it is wired, not required (ADR §7 W1): the tree test
reports its findings as a skip -- on 3.17.2 it finds `code-index` (agents/developer.md, staff-engineer.md).
Run: python3 tests/test_skill_names.py           unit + mutation tests (CI gate #27)
     python3 tests/test_skill_names.py --scan    findings (--v4: 4.0.0 rules); exit 1 when any
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_agent_tools_pin import frontmatter, v4_required  # noqa: E402  (one data switch for all v4 gates)

LOAD_VERB = re.compile(r"(?<![A-Za-z])(?:load|loads|invoke|invokes|Skill)(?![A-Za-z-])|โหลด")
SPAWN_VERB = re.compile(r"(?<![A-Za-z_])(?:spawn(?:s|ed|ing)?|dispatch(?:es|ed|ing)?|delegate(?:s|d)?|"
                        r"subagent_type|agentType)(?![A-Za-z_])|(?<![A-Za-z_])(?:Agent|Task)\(", re.I)
NAME = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
PAREN = re.compile(r"\([^()]*\)")
CLAUSE_END = re.compile(r"\.\s|\.$|;|→|\|")
# a load clause also ends at "then" or a spawn verb ("load `x` first, then dispatch `y`"); `·` separates load lists
LOAD_END = re.compile(r"\.\s|\.$|;|→|\||(?<![A-Za-z])then(?![A-Za-z])|(?<![A-Za-z_])(?:spawn|dispatch|delegate)", re.I)
FORMERLY = re.compile(r"formerly (?:the )?$")
MARKER = "tombstone-allow"


def retired_agents(root=ROOT):
    """Agent types retired through the single retired-names ledger (W10 adds agents/orchestrator.md)."""
    try:
        from test_team_package import RETIRED
    except ImportError:
        return set()
    return {pathlib.PurePosixPath(p).stem for p in RETIRED if p.startswith("agents/")}


class Context:
    def __init__(self, root=ROOT):
        self.root = root
        manifest = json.loads((root / ".claude-plugin/plugin.json").read_text())
        self.plugin = manifest["name"]
        self.buckets = [s.strip("./").split("/")[-1] for s in manifest["skills"]]
        self.skills = {p.parent.name for b in self.buckets for p in (root / "skills" / b).glob("*/SKILL.md")}
        self.agents = {p.stem for p in (root / "agents").glob("*.md")}
        self.commands = {p.stem for p in (root / "commands").glob("*.md")}
        self.styles = set()
        for p in (root / "output-styles").glob("*.md"):
            self.styles.add(p.stem)
            name = next((l[5:].strip().strip("\"'") for l in frontmatter(p.read_text()) or [] if l.startswith("name:")), "")
            self.styles.add(name)
        self.namespaced_ok = self.skills | self.agents | self.commands | self.styles
        self.retired = retired_agents(root)
        self.load_tok = re.compile(r"`(%s:)?(%s)`" % (re.escape(self.plugin), NAME))
        self.skill_word = re.compile(r"`(%s:)?(%s)` skill\b" % (re.escape(self.plugin), NAME))
        self.skill_call = re.compile(r"(?<![A-Za-z])Skill\(\s*[`\"'](%s:)?(%s)[`\"']" % (re.escape(self.plugin), NAME))
        self.namespaced = re.compile(r"(?<![\w.-])%s:([A-Za-z0-9][A-Za-z0-9-]*)" % re.escape(self.plugin))
        self.spawn_tok = re.compile(r"[`\"'](%s:)?(%s)[`\"']" % (re.escape(self.plugin), NAME))
        self.spawn_kv = re.compile(r"(?:subagent_type|agentType)[\"']?\s*[:=]\s*[`\"']?(%s:)?(%s)\b"
                                   % (re.escape(self.plugin), NAME))
        # a quoted literal value (a variable such as `it.type` is not a name)
        self.spawn_kv_lit = re.compile(r"(?:subagent_type|agentType)[\"']?\s*[:=]\s*([`\"'])(%s:)?(%s)\1"
                                       % (re.escape(self.plugin), NAME))

    def shipped_files(self):
        allow = self.root / ".pack-allowlist"
        if allow.is_file():
            entries = [l.split()[0] for l in allow.read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]
        else:
            entries = ["agents", "commands", "output-styles", "references"] + ["skills/" + b for b in self.buckets]
        files = []
        for e in entries:
            p = self.root / e
            files += [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file()) if p.is_dir() else []
        return [f for f in files if f.suffix in (".md", ".js") and "__pycache__" not in f.parts]

    def spawn_scope(self, rel):
        return rel.startswith(("output-styles/", "commands/", "references/")) or \
            any(rel.startswith(f"skills/{b}/") for b in self.buckets)


def preload_findings(ctx, rel, text, v4):
    out = []
    for i, line in enumerate(text.splitlines()[: len(frontmatter(text) or []) + 2], 1):
        if not line.startswith("skills:"):
            continue
        try:
            names = json.loads(line[len("skills:"):].strip())
        except ValueError:
            return [f"{rel}:{i}: skills: is not a one-line JSON array"]
        for n in names if isinstance(names, list) else []:
            base = n.split(":", 1)[1] if n.startswith(ctx.plugin + ":") else n
            if base not in ctx.skills:
                out.append(f"{rel}:{i}: preload '{n}' is not a shipped skill")
            elif v4 and base == n:
                out.append(f"{rel}:{i}: bare preload '{n}' (4.0.0: '{ctx.plugin}:{n}')")
    return out


def text_findings(ctx, rel, text, v4):
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if MARKER in line:
            continue
        loads = [(m.group(1), m.group(2)) for m in ctx.skill_call.finditer(line)]  # (prefix or None, name)
        s = line
        while PAREN.search(s):
            s = PAREN.sub(" ", s)
        for m in ctx.skill_word.finditer(s):
            if not FORMERLY.search(s[:m.start()]):
                loads.append((m.group(1), m.group(2)))
        plain = re.sub(r"`[^`]*`", lambda m: "\0" * len(m.group(0)), s)
        for v in LOAD_VERB.finditer(plain):
            clause = LOAD_END.split(s[v.end():])[0]
            off = v.end()
            for m in ctx.load_tok.finditer(clause):
                if not FORMERLY.search(s[:off + m.start()]):
                    loads.append((m.group(1), m.group(2)))
        for prefix, name in dict.fromkeys(loads):
            if name not in ctx.skills:
                out.append(f"{rel}:{i}: load '{(prefix or '') + name}' is not a shipped skill")
            elif v4 and not prefix:
                out.append(f"{rel}:{i}: bare load '{name}' (4.0.0: '{ctx.plugin}:{name}')")
        for m in ctx.namespaced.finditer(line):
            if m.group(1) not in ctx.namespaced_ok and not FORMERLY.search(line[:m.start()]):
                out.append(f"{rel}:{i}: '{ctx.plugin}:{m.group(1)}' names no shipped skill, agent, command or style")
        if ctx.spawn_scope(rel):
            keyed = {(m.group(2), m.group(3)) for m in ctx.spawn_kv_lit.finditer(line)}
            spawned = [(m.group(1), m.group(2)) for m in ctx.spawn_kv.finditer(line)]
            for v in SPAWN_VERB.finditer(line):
                spawned += [(m.group(1), m.group(2)) for m in ctx.spawn_tok.finditer(CLAUSE_END.split(line[v.end():])[0])]
            for prefix, name in dict.fromkeys(spawned):
                if name in ctx.retired:
                    out.append(f"{rel}:{i}: spawn of retired agent type '{(prefix or '') + name}'")
                elif name in ctx.agents and not prefix:
                    out.append(f"{rel}:{i}: spawn by bare type '{name}' (use '{ctx.plugin}:{name}'; a bare name is served by a project agent)")
                elif name not in ctx.agents and (prefix, name) in keyed:
                    out.append(f"{rel}:{i}: subagent_type/agentType '{(prefix or '') + name}' names no agent")
    return out


def scan(root=ROOT, force_v4=False):
    ctx, v4 = Context(root), force_v4 or v4_required(root)
    found = []
    for f in ctx.shipped_files():
        rel, text = f.relative_to(root).as_posix(), f.read_text(errors="ignore")
        if rel.startswith("agents/") and rel.endswith(".md"):
            found += preload_findings(ctx, rel, text, v4)
        found += text_findings(ctx, rel, text, v4)
    return found


class SkillNamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = Context()
        cls.p = cls.ctx.plugin

    def find(self, text, rel="agents/x.md", v4=False):
        return text_findings(self.ctx, rel, text, v4)

    def test_sets_are_read_from_files(self):
        self.assertIn("shode-house-discipline", self.ctx.skills)
        self.assertNotIn("eval-harness", self.ctx.skills)          # in-progress/ never counts as shipped
        self.assertEqual({p.stem for p in (ROOT / "agents").glob("*.md")}, self.ctx.agents)
        self.assertTrue(self.ctx.shipped_files())

    def test_tree(self):
        found = scan()
        if v4_required():
            self.assertEqual([], found)
        elif found:
            self.skipTest(f"A8 advisory until 4.0.0 (ADR §7 W1), {len(found)} finding(s): " + " | ".join(found))

    def test_todays_dangling_code_index_is_found_while_present(self):
        dev = ROOT / "agents/developer.md"
        if "`code-index`" not in dev.read_text():
            self.skipTest("code-index already removed from agents/developer.md")
        self.assertTrue(any(f.startswith("agents/developer.md:") and "'code-index'" in f for f in scan()))

    # --- mutations: a planted dangling name / bare spawn must be red ---
    def test_planted_dangling_load_is_found(self):
        self.assertEqual(["agents/x.md:1: load 'no-such-skill' is not a shipped skill"],
                         self.find("Read prerequisites once; load `dev-gate` (gates), `no-such-skill` (x). Then go."))

    def test_planted_dangling_namespaced_load_is_found(self):
        self.assertIn(f"agents/x.md:1: load '{self.p}:no-such-skill' is not a shipped skill",
                      self.find(f"โหลด `{self.p}:no-such-skill` ก่อนเริ่ม"))
        self.assertIn(f"agents/x.md:1: '{self.p}:no-such-skill' names no shipped skill, agent, command or style",
                      self.find(f"see {self.p}:no-such-skill"))

    def test_skill_word_form_and_formerly_exemption(self):
        self.assertTrue(self.find("use the `ghost-skill` skill here"))
        self.assertEqual([], self.find("formerly the `meeting` skill (merged v3.17)"))
        self.assertEqual([], self.find("load `ghost-skill` <!-- tombstone-allow -->"))

    def test_spawn_after_a_load_is_not_a_load(self):
        found = self.find("bug → load `diagnose` first, then dispatch `developer` · review", "output-styles/s.md")
        self.assertEqual(1, len(found), found)
        self.assertIn("spawn by bare type 'developer'", found[0])

    def test_parenthesised_and_next_clause_names_are_not_loads(self):
        self.assertEqual([], self.find("โหลด `data-migration` ก่อน (gate `pre-data-migration` อยู่ที่นั่น). Online DDL: `pt-online-schema-change`"))

    def test_planted_dangling_preload_is_found(self):
        text = '---\nname: x\nskills: ["shode-house-discipline", "%s:ghost"]\n---\nbody\n' % self.p
        self.assertEqual(["agents/x.md:3: preload '%s:ghost' is not a shipped skill" % self.p],
                         preload_findings(self.ctx, "agents/x.md", text, False))

    def test_v4_requires_namespaced_preload_and_load(self):
        text = '---\nname: x\nskills: ["shode-house-discipline"]\n---\n'
        self.assertEqual([], preload_findings(self.ctx, "agents/x.md", text, False))
        self.assertIn("bare preload", preload_findings(self.ctx, "agents/x.md", text, True)[0])
        self.assertEqual([], preload_findings(self.ctx, "agents/x.md", text.replace('["', '["%s:' % self.p), True))
        self.assertIn("bare load 'dev-gate'", self.find("load `dev-gate` now", v4=True)[0])
        self.assertEqual([], self.find(f"load `{self.p}:dev-gate` now", v4=True))

    def test_planted_bare_spawn_is_found_in_style_commands_skills_only(self):
        line = "Then dispatch `developer` with the task path."
        for rel in ("output-styles/s.md", "commands/c.md", "skills/workflow/ask/SKILL.md", "references/runbooks/r.md"):
            self.assertEqual([f"{rel}:1: spawn by bare type 'developer' (use '{self.p}:developer'; a bare name is served by a project agent)"],
                             self.find(line, rel))
        self.assertEqual([], self.find(line, "agents/x.md"))                 # agents/: no spawn tool from 4.0.0 (A1)
        self.assertEqual([], self.find(line.replace("`developer`", f"`{self.p}:developer`"), "commands/c.md"))
        self.assertTrue(self.find('subagent_type: "code-reviewer"', "commands/c.md"))
        self.assertTrue(self.find("agent(prompt, { agentType: 'qa-engineer' })", "skills/ops/drain/x.js"))
        self.assertEqual([], self.find("agent(prompt, { agentType: it.type })", "skills/ops/drain/x.js"))

    def test_spawn_of_a_non_agent_or_retired_name_is_found(self):
        """Chris W1 Low 3: the key form must name an agent; a retired type is red in any spawn form."""
        self.assertEqual(['commands/c.md:1: subagent_type/agentType \'ghost-agent\' names no agent'],
                         self.find('subagent_type: "ghost-agent"', "commands/c.md"))
        self.assertTrue(self.find(f"agent(p, {{ agentType: '{self.p}:ghost-agent' }})", "skills/ops/drain/x.js"))
        self.assertEqual([], self.find(f'subagent_type: "{self.p}:developer"', "commands/c.md"))
        ctx = Context()
        ctx.retired = {"orchestrator"}                                      # what W10's RETIRED entry will add
        for text in ("dispatch `orchestrator` now", f"dispatch `{self.p}:orchestrator` now"):
            self.assertTrue(any("retired agent type" in f for f in text_findings(ctx, "commands/c.md", text, False)), text)

    def test_retired_agents_come_from_the_ledger(self):
        from test_team_package import RETIRED
        self.assertEqual({pathlib.PurePosixPath(p).stem for p in RETIRED if p.startswith("agents/")}, self.ctx.retired)

    def test_skill_call_form_is_a_load(self):
        """Chris W1 Low 4: Skill(`x`) is a load even though the parenthesis is otherwise removed."""
        self.assertEqual(["agents/x.md:1: load 'ghost-skill' is not a shipped skill"],
                         self.find("use Skill(`ghost-skill`) now"))
        self.assertEqual(["agents/x.md:1: load 'ghost-skill' is not a shipped skill"],
                         self.find('call Skill("ghost-skill") first'))
        self.assertEqual([], self.find(f'call Skill("{self.p}:dev-gate") first', v4=True))
        self.assertIn("bare load 'dev-gate'", self.find("call Skill(`dev-gate`)", v4=True)[0])


if __name__ == "__main__":
    if "--scan" in sys.argv:
        found = scan(force_v4="--v4" in sys.argv)
        print("\n".join(found) if found else "ok skill names")
        sys.exit(1 if found else 0)
    unittest.main()
