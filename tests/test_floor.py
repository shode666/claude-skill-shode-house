#!/usr/bin/env python3
"""scripts/floor.py -- safety floor single source + sha256 copies (v4 ADR §5.5.2, slice W4).

Mutation tests run on a throw-away fixture tree; the last class checks the real canonical files.
The outside-marker lint (a relaxing clause appended after `floor:end`) is W1's A16(b)
(tests/test_shipped_text_lint.py); the hash check here deliberately covers the block only.
Run: python3 tests/test_floor.py   (also collected by pytest)
"""
import hashlib, importlib.util, os, pathlib, re, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/floor.py"
BODY = "<!-- floor:begin -->\n## Safety floor (fixture)\n- R0: confirm first.\n- Redact secrets.\n<!-- floor:end -->\n"
STYLE = "<!-- floor:style:begin -->\n## Safety floor (main, fixture)\n- R0: confirm first.\n<!-- floor:style:end -->\n"
AGENTS = ("build", "verify")


def agent(name, block):
    """R44: the begin marker is the first non-blank line after the frontmatter."""
    return f"---\nname: {name}\nskills: [\"shode-house-discipline\"]\n---\n\n{block}\nIntro line.\n\n## Role\n- role rule\n"


def style(block):
    return f"---\nname: shode-house\ndescription: router\n---\n\n{block}\n## Routing\n- route\n"


ASK_ADAPTER = "plugins/shode-house/skills/ask/SKILL.md"


def adapter(block):
    """Generated `ask` adapter: the skills-only host carrier of the style floor (ADR erratum 1 §5.8.1)."""
    return f"---\nname: ask\ndescription: entry\n---\n\n{block}\nUse the referenced skill as the entry point.\n"


class FloorFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.put(".safety-floor/body.md", BODY)
        self.put(".safety-floor/style.md", STYLE)
        self.put(".claude-plugin/plugin.json", '{"name": "shode-house", "version": "3.17.2"}\n')
        for a in AGENTS:
            self.put(f"agents/{a}.md", agent(a, BODY))
            self.put(f"plugins/shode-house/agents/{a}.md", agent(a, BODY) + "\nfooter\n")
            self.put(f"plugins/shode-house/knowledge/agents/{a}.md", agent(a, BODY))
        self.put("output-styles/shode-house.md", style(STYLE))
        self.put("plugins/shode-house/output-styles/shode-house.md", style(STYLE))
        self.put("plugins/shode-house/knowledge/output-styles/shode-house.md", style(STYLE))
        self.put(ASK_ADAPTER, adapter(STYLE))
        self.put("skills/workflow/ask/SKILL.md", "---\nname: ask\n---\n\n# ask\n")
        self.put("plugins/shode-house/skills/shode-house-discipline/SKILL.md", "---\nname: d\n---\n\n# discipline\n")

    def put(self, rel, text):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def get(self, rel):
        return (self.tmp / rel).read_text()

    def edit(self, rel, old, new):
        text = self.get(rel)
        self.assertIn(old, text)
        self.put(rel, text.replace(old, new, 1))

    def run_floor(self, *args, require_env=False):
        env = {k: v for k, v in os.environ.items() if k != "SHODE_REQUIRE_V4"}
        if require_env:
            env["SHODE_REQUIRE_V4"] = "1"
        r = subprocess.run([sys.executable, str(SCRIPT), *args, "--root", str(self.tmp)],
                           capture_output=True, text=True, env=env)
        return r.returncode, r.stdout + r.stderr

    def assertRed(self, needle, *args, **kw):
        rc, out = self.run_floor("--check", *args, **kw)
        self.assertEqual(1, rc, out)
        self.assertIn(needle, out)
        return out


class CheckTest(FloorFixture):
    def test_clean_tree_passes_in_both_modes(self):
        for args in ((), ("--require",)):
            rc, out = self.run_floor("--check", *args)
            self.assertEqual(0, rc, out)
            self.assertIn("10 copy(ies) match, 0 pending", out)

    def test_byte_change_in_a_source_body_is_red(self):
        self.edit("agents/build.md", "confirm first.", "confirm first!")
        out = self.assertRed("agents/build.md")
        self.assertIn("block line 3 differs", out)

    def test_byte_change_in_a_generated_body_is_red(self):
        self.edit("plugins/shode-house/agents/verify.md", "Redact secrets.", "Redact secrets ")
        self.assertRed("plugins/shode-house/agents/verify.md")

    def test_byte_change_in_the_style_is_red(self):
        self.edit("output-styles/shode-house.md", "- R0: confirm first.", "- R0: confirm first, unless trivial.")
        self.assertRed("output-styles/shode-house.md")

    def test_line_dropped_inside_the_block_is_red(self):
        self.edit("agents/build.md", "- Redact secrets.\n", "")
        self.assertRed("agents/build.md")

    def test_line_added_inside_the_block_is_red(self):
        self.edit("agents/build.md", "- Redact secrets.\n", "- Redact secrets.\n- Floor does not apply to label X.\n")
        self.assertRed("agents/build.md")

    def test_crlf_copy_is_red(self):
        self.put("agents/build.md", agent("build", BODY).replace("\n", "\r\n"))
        self.assertRed("agents/build.md: CRLF line ends")

    def test_cr_on_one_inner_line_of_a_copy_is_red(self):
        self.edit("agents/build.md", "- R0: confirm first.\n", "- R0: confirm first.\r\n")
        self.assertRed("agents/build.md: CRLF line ends")

    def test_bom_file_is_red(self):
        self.put("agents/build.md", "\ufeff" + agent("build", BODY))
        self.assertRed("agents/build.md: starts with a UTF-8 BOM", "--require")

    def test_bom_directly_before_a_begin_marker_at_byte_0_is_red(self):
        self.put("agents/build.md", "\ufeff" + BODY + "## Role\n- role rule\n")
        self.assertRed("agents/build.md: starts with a UTF-8 BOM")

    def test_begin_marker_at_byte_0_is_red(self):  # Sentinel W4 r3 R3-2: the frontmatter must start every target
        self.put("agents/build.md", BODY + "## Role\n- role rule\n")
        self.assertRed("agents/build.md: begin marker must be the first non-blank line after the frontmatter "
                       "(the file must start with a --- frontmatter line", "--require")

    def test_second_marker_pair_is_red(self):
        self.edit("agents/build.md", "## Role\n", BODY + "## Role\n")
        self.assertRed("needs exactly one marker pair")

    def test_unpaired_marker_is_red(self):
        self.edit("agents/build.md", "<!-- floor:end -->\n", "")
        self.assertRed("needs exactly one marker pair")

    def test_missing_begin_marker_is_red(self):
        self.edit("agents/build.md", "<!-- floor:begin -->\n", "")
        self.assertRed("needs exactly one marker pair (found begin x0, end x1")

    def test_reversed_markers_are_red(self):
        text = agent("build", "<!-- floor:end -->\n- x\n<!-- floor:begin -->\n")
        self.put("agents/build.md", text)
        self.assertRed("end marker before begin marker")

    def test_indented_begin_marker_is_red(self):
        self.edit("agents/build.md", "<!-- floor:begin -->", "  <!-- floor:begin -->")
        self.assertRed("begin marker must be a whole line")

    def test_trailing_text_after_end_marker_is_red(self):
        self.edit("agents/build.md", "<!-- floor:end -->\n", "<!-- floor:end --> trailing\n")
        self.assertRed("end marker must be a whole line")

    def test_stray_floor_marker_text_is_red(self):
        self.edit("agents/build.md", "- role rule\n", "- role rule <!-- floor:begin\n")
        self.assertRed("needs exactly one marker pair")

    def test_style_floor_in_an_agent_is_red(self):
        self.put("agents/build.md", agent("build", STYLE))
        self.assertRed("carries the style floor markers")

    def test_body_floor_in_a_style_is_red(self):
        self.put("output-styles/shode-house.md", style(BODY))
        self.assertRed("carries the body floor markers")

    def test_missing_markers_pending_until_required(self):
        self.put("agents/build.md", agent("build", ""))
        rc, out = self.run_floor("--check", "--verbose")
        self.assertEqual(0, rc, out)
        self.assertIn("~ pending agents/build.md: no floor markers", out)
        self.assertIn("1 pending", out)
        self.assertRed("agents/build.md: no floor markers -- required", "--require")
        self.assertRed("agents/build.md: no floor markers -- required", require_env=True)
        self.put(".claude-plugin/plugin.json", '{"name": "shode-house", "version": "4.0.0"}\n')
        self.assertRed("agents/build.md: no floor markers -- required")

    def test_empty_marker_pair_pending_until_required(self):
        self.put("agents/build.md", agent("build", "<!-- floor:begin -->\n<!-- floor:end -->\n"))
        rc, out = self.run_floor("--check", "--verbose")
        self.assertEqual(0, rc, out)
        self.assertIn("text not written yet", out)
        self.assertRed("text not written yet", "--require")

    def test_required_mode_needs_a_source_style(self):
        os.remove(self.tmp / "output-styles/shode-house.md")
        self.assertRed("style floor: no file matches output-styles/*.md", "--require")

    def test_required_mode_needs_the_ask_adapter(self):  # Sentinel R2-5
        os.remove(self.tmp / ASK_ADAPTER)
        self.assertEqual(0, self.run_floor("--check")[0])
        self.assertRed("style floor: no file matches plugins/*/skills/ask/SKILL.md -- required", "--require")

    def test_required_mode_needs_the_generated_tree(self):  # Sentinel R2-5
        shutil.rmtree(self.tmp / "plugins")
        rc, out = self.run_floor("--check")
        self.assertEqual(0, rc, out)
        out = self.assertRed("body floor: no file matches plugins/*/agents/*.md", "--require")
        for pattern in ("plugins/*/knowledge/agents/*.md", "plugins/*/output-styles/*.md",
                        "plugins/*/knowledge/output-styles/*.md", "plugins/*/skills/ask/SKILL.md"):
            self.assertIn(f"no file matches {pattern} -- required", out)

    def test_canonical_must_be_one_clean_block(self):
        cases = {
            "outside": BODY + "- appended after the end marker\n",
            "non-ascii": BODY.replace("Redact", "Re​dact"),
            "no final newline": BODY.rstrip("\n"),
            "crlf": BODY.replace("\n", "\r\n"),
            "cr on an inner line": BODY.replace("- R0: confirm first.\n", "- R0: confirm first.\r\n"),
            "empty": "<!-- floor:begin -->\n<!-- floor:end -->\n",
            "second pair": BODY + BODY,
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                self.put(".safety-floor/body.md", text)
                for mode in ("--check", "--write"):
                    rc, out = self.run_floor(mode)
                    self.assertEqual(2, rc, out)
                    self.assertIn("canonical floor invalid", out)


class PlacementTest(FloorFixture):
    """R44 (W4-5 / S4-1 / S4r2-2 / R2-3): the begin marker must be the first non-blank line after the frontmatter,
    so no fence, comment, quote or framing text can wrap the block. Red in both modes; --write refuses."""
    MSG = "begin marker must be the first non-blank line after the frontmatter"

    def assertMisplaced(self, text, rel="agents/build.md"):
        self.put(rel, text)
        for args in ((), ("--require",)):
            with self.subTest(mode=args):
                self.assertRed(f"{rel}: {self.MSG}", *args)
        rc, out = self.run_floor("--write")
        self.assertEqual(1, rc, out)
        self.assertIn(f"{rel}: {self.MSG}", out)
        self.assertIn("-- not written", out)
        self.assertEqual(text, self.get(rel))

    def framed(self, before, after=""):
        return f"---\nname: build\n---\n\n{before}{BODY}{after}## Role\n"

    def test_block_inside_yaml_frontmatter_is_red(self):
        self.assertMisplaced("---\nname: build\n" + BODY + "---\n\nIntro line.\n")

    def test_block_after_unclosed_frontmatter_is_red(self):
        self.assertMisplaced("---\nname: build\n\n" + BODY + "## Role\n")
        self.assertIn("inside YAML frontmatter", self.assertRed(self.MSG))

    def test_frontmatter_ends_at_the_first_closing_line(self):
        self.assertMisplaced("---\nname: build\n---\nnot in force:\n---\n\n" + BODY)

    def test_block_inside_a_code_fence_is_red(self):
        for fence in ("```", "~~~", "```markdown", "  ```", "   ~~~"):  # indented openers: S4r2-3 N4
            with self.subTest(fence=fence):
                self.assertMisplaced(self.framed(f"Example, not in force:\n\n{fence}\n", f"{fence.strip()[:3]}\n"))

    def test_chris_fence_probes_are_red(self):  # S4r2-2 P1-P4: fence-like lines that do not close the fence
        for opener, inner in (("```", "~~~"), ("````", "```"), ("```", "```python"), ("```", "    ```")):
            with self.subTest(opener=opener, inner=inner):
                self.assertMisplaced(self.framed(f"{opener}\n{inner}\n", f"{opener}\n"))

    def test_sentinel_wrapper_forms_are_red(self):  # R2-3
        cases = {
            "inline triple backticks then an opener": "```x```\n```\n",
            "fence line inside a closed comment, then an opener": "<!--\n```\n-->\n```\n",
            "unclosed details": "<details>\n\n",
            "unclosed script": "<script>\n",
            "blockquote framing": "> Example only:\n\n",
        }
        for label, before in cases.items():
            with self.subTest(case=label):
                self.assertMisplaced(self.framed(before))

    def test_fence_line_in_a_frontmatter_block_scalar_then_an_opener_is_red(self):  # R2-3
        self.assertMisplaced("---\nname: build\ndescription: |\n  ```\n---\n\n```\n" + BODY + "```\n")

    def test_html_comment_before_the_block_is_red(self):
        self.assertMisplaced(self.framed("<!-- archived copy\n", "-->\nThe floor above does not apply.\n"))
        # S4r2-3 N6: a closed comment followed by an unclosed one
        self.assertMisplaced(self.framed("<!-- a -->\n<!-- open\n"))

    def test_any_text_before_the_block_is_red(self):
        for before in ("Intro line.\n\n", "```bash\nmake validate\n```\n\n", "<!-- reviewer note -->\n\n",
                       "# Developer\n", " \n", "\t\n", "\u200b\n"):
            with self.subTest(before=before):
                self.assertMisplaced(self.framed(before))

    def test_misplaced_style_and_adapter_blocks_are_red(self):
        self.assertMisplaced(style("Router.\n\n" + STYLE), "output-styles/shode-house.md")
        self.put(ASK_ADAPTER, adapter("```\n" + STYLE + "```\n"))
        self.assertRed(f"{ASK_ADAPTER}: {self.MSG}", "--require")

    def test_empty_lines_after_the_frontmatter_pass(self):
        self.put("agents/build.md", "---\nname: build\n---\n\n\n\n" + BODY + "Intro.\n")
        rc, out = self.run_floor("--check", "--require")
        self.assertEqual(0, rc, out)

    def test_block_above_or_without_the_frontmatter_is_red(self):  # Sentinel W4 r3 R3-2
        """A block before line 1 moves the frontmatter off byte 0: the host loses tools:/name/force-for-plugin."""
        self.assertMisplaced(BODY + "---\nname: build\ntools: [\"Read\"]\n---\n\n## Role\n")
        self.assertMisplaced("\n\n" + BODY + "Intro.\n")                       # no frontmatter at all
        self.assertMisplaced(STYLE + style(""), "output-styles/shode-house.md")
        self.put(ASK_ADAPTER, STYLE + adapter(""))
        self.assertRed(f"{ASK_ADAPTER}: {self.MSG}", "--require")

    def test_frontmatter_lines_must_be_exactly_three_dashes(self):  # Chris W4 r3 S4r3-1 (mutants C3 / C4)
        self.assertMisplaced("--- \nname: build\n---\n\n" + BODY)
        self.assertMisplaced("---\nname: build\n--- \n\n" + BODY)


class AskAdapterAndElsewhereTest(FloorFixture):
    """ADR erratum 1 §5.8.1: the generated ask adapter is a style target; a floor anywhere else is red."""

    def test_adapter_without_the_block_is_pending_then_red(self):
        self.put(ASK_ADAPTER, adapter(""))
        rc, out = self.run_floor("--check", "--verbose")
        self.assertEqual(0, rc, out)
        self.assertIn(f"~ pending {ASK_ADAPTER}: no floor markers", out)
        self.assertRed(f"{ASK_ADAPTER}: no floor markers -- required", "--require")

    def test_adapter_empty_pair_is_pending_before_4(self):
        self.put(ASK_ADAPTER, adapter("<!-- floor:style:begin -->\n<!-- floor:style:end -->\n"))
        rc, out = self.run_floor("--check")
        self.assertEqual(0, rc, out)
        self.assertIn("1 pending", out)
        self.assertRed(f"{ASK_ADAPTER}: markers present, text not written yet", "--require")

    def test_adapter_byte_change_is_red(self):
        self.edit(ASK_ADAPTER, "confirm first.", "confirm first if risky.")
        self.assertRed(f"{ASK_ADAPTER}: style floor sha256")

    def test_adapter_with_the_body_floor_is_red(self):
        self.put(ASK_ADAPTER, adapter(BODY))
        self.assertRed(f"{ASK_ADAPTER}: carries the body floor markers")

    def test_block_in_the_tree_discipline_root_is_red_in_both_modes(self):
        rel = "plugins/shode-house/skills/shode-house-discipline/SKILL.md"
        self.put(rel, "---\nname: d\n---\n\n" + STYLE + "\n# discipline\n")
        for args in ((), ("--require",)):
            with self.subTest(mode=args):
                out = self.assertRed(f"{rel}: floor marker outside a floor target (floor elsewhere)", *args)
                self.assertIn(f"{rel}: floor text line 6 outside a floor target", out)

    def test_block_in_the_source_ask_skill_is_red(self):
        self.put("skills/workflow/ask/SKILL.md", "---\nname: ask\n---\n\n" + STYLE + "\n# ask\n")
        self.assertRed("skills/workflow/ask/SKILL.md: floor marker outside a floor target (floor elsewhere)")

    def test_marker_text_in_other_shipped_dirs_is_red(self):
        for rel in ("references/runbooks/x.md", "commands/ask.md", "agents/sub/notes.md",
                    "plugins/shode-house/knowledge/skills/workflow/ask/SKILL.md", "plugins/shode-house/HOST-NOTES.md"):
            with self.subTest(file=rel):
                self.put(rel, "text <!-- floor:begin --> text\n")
                self.assertRed(f"{rel}: floor marker outside a floor target (floor elsewhere)")
                os.remove(self.tmp / rel)

    def test_floor_lines_pasted_without_markers_are_red(self):
        rel = "plugins/shode-house/skills/shode-house-discipline/SKILL.md"
        for line in ("## Safety floor (pasted copy)", "- R0 (irreversible: force-push): confirm first.",
                     "  - R0 (irreversible: indented paste)"):
            with self.subTest(line=line):
                self.put(rel, f"---\nname: d\n---\n\n# discipline\n{line}\n")
                self.assertRed(f"{rel}: floor text line 6 outside a floor target (floor elsewhere)")
                self.assertRed(f"{rel}: floor text line 6", "--require")

    def test_marker_in_an_output_styles_subdir_is_red(self):  # S4r2-3 N18
        self.put("output-styles/archive/old.md", "<!-- floor:style:begin -->\n")
        self.assertRed("output-styles/archive/old.md: floor marker outside a floor target (floor elsewhere)")

    def test_normalised_floor_line_variants_are_red(self):  # Sentinel R2-2 / Chris S4r2-6
        rel = "references/notes.md"
        variants = ("## Safety Floor (pasted)", "### Safety floor (pasted)", "##  Safety floor (pasted)", "## Safety  floor (inner spaces)", "- R0  (irreversible: x)",
                    "**Safety floor (pasted)**", "Safety floor (no prefix)", "SAFETY FLOOR (upper)",
                    "\ufeff## Safety floor (BOM)", "\u200b## Safety floor (zero-width)", "## Safety\u00a0floor (NBSP)",
                    "> ## Safety floor (quoted)", "## Safety floor(no space)", "\uff03\uff03 Safety floor (fullwidth)",
                    "* R0 (irreversible: x)", "- **R0** (irreversible: x)", "1. R0 (irreversible: x)",
                    "- R0 (irreversible : x)", "-\u00a0R0 (irreversible: x)", "> - R0 (irreversible: x)",
                    "R0 (irreversible: no prefix)", "\t- r0 (IRREVERSIBLE: x)", "- `R0` (irreversible: x)",
                    "- R\u200b0 (irreversible: x)",
                    # Sentinel W4 r3 R3-1: leading markup a near-verbatim paste may carry
                    "\\- R0 (irreversible: x)", "- [ ] R0 (irreversible: x)", "- [x] R0 (irreversible: x)",
                    "[R0 (irreversible: x](y)", "~~R0 (irreversible: x~~", "<b>R0</b> (irreversible: x)",
                    "&#82;0 (irreversible: x)", "\\#\\# Safety floor (escaped)", "<h2>Safety floor (html)</h2>",
                    "R0&nbsp;(irreversible: x)", "&lt;b&gt;R0&lt;/b&gt; (irreversible: x)")
        for line in variants:
            with self.subTest(line=line):
                self.put(rel, f"# notes\n{line}\n")
                self.assertRed(f"{rel}: floor text line 2 outside a floor target (floor elsewhere)")

    def test_marker_spelling_variants_are_red(self):  # Sentinel R2-2
        rel = "commands/x.md"
        for mark in ("<!--floor:begin-->", "<!--  floor:begin -->", "<!-- FLOOR:begin -->", "<!-- floor :begin -->",
                     "<!--\u200bfloor:begin -->", "<!--\tfloor:style:end -->",
                     "\uff1c!-- floor:begin --\uff1e"):  # Chris W4 r3 S4r3-2: full-width, needs NFKC (mutant C25)
            with self.subTest(mark=mark):
                self.put(rel, f"text\n{mark}\n")
                self.assertRed(f"{rel}: floor marker outside a floor target (floor elsewhere)")

    # Sentinel W1 follow-up F3: every invisible character, not a fixed list -- Unicode Cf plus the
    # Default_Ignorable_Code_Point ranges that are not Cf. Sentinel's 8 code points, each also as an entity.
    F3_INVISIBLE = ("‪", "⁦", "⁢", "͏", "️", "︀", "\U000e0020", "ㅤ")

    def test_any_invisible_character_in_a_floor_line_is_red(self):
        rel = "references/notes.md"
        for ch in self.F3_INVISIBLE:
            for form in (ch, "&#x%x;" % ord(ch)):
                for line in (f"- R{form}0 (irreversible: x)", f"## Safety{form} floor (pasted)", f"{form}## Safety floor (x)"):
                    with self.subTest(code=f"U+{ord(ch):04X}", line=line):
                        self.put(rel, f"# notes\n{line}\n")
                        self.assertRed(f"{rel}: floor text line 2 outside a floor target (floor elsewhere)")

    def test_any_invisible_character_in_a_marker_spelling_is_red(self):
        rel = "commands/x.md"
        for ch in self.F3_INVISIBLE:
            with self.subTest(code=f"U+{ord(ch):04X}"):
                self.put(rel, f"text\n<!--{ch}floor:begin -->\n")
                self.assertRed(f"{rel}: floor marker outside a floor target (floor elsewhere)")

    def test_invisible_rule_is_cf_plus_default_ignorable(self):
        spec = importlib.util.spec_from_file_location("floor_f3", SCRIPT)
        fl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fl)
        for ch in self.F3_INVISIBLE + ("​", "­", "﻿", "᠎", "ᅟ", "ﾠ", "\U000e0100"):
            self.assertTrue(fl.invisible(ch), f"U+{ord(ch):04X}")
        for ch in ("R", "0", " ", " ", "ก", "ำ", "́", "Ｒ"):   # visible, or handled by NFKC
            self.assertFalse(fl.invisible(ch), f"U+{ord(ch):04X}")
        self.assertEqual("R0", fl.visible("R‪⁦⁢͏️︀\U000e0020ㅤ0"))

    def test_invisible_rule_covers_every_table_range_and_cf_outside_it(self):
        """Chris W10a-C1: one code point per non-Cf Default_Ignorable range (written out, never read from the table,
        which would be tautological) and Cf points outside the table, so neither half of invisible() can go."""
        spec = importlib.util.spec_from_file_location("floor_c1", SCRIPT)
        fl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fl)
        import unicodedata
        non_cf = ("឴", "឵", "᠋", "᠏", "￰", "￸", "⁥", "\U000e01f0", "\U000e0fff",
                  "ᅟ", "͏", "ㅤ", "ﾠ", "️")
        for ch in non_cf:
            with self.subTest(code=f"U+{ord(ch):04X}"):
                self.assertNotEqual("Cf", unicodedata.category(ch))      # the table half decides these
                self.assertTrue(fl.invisible(ch))
        cf_outside = ("￹", "￻", "؀", "۝", "܏", "\U000110bd", "\U00013430")
        for ch in cf_outside:
            with self.subTest(code=f"U+{ord(ch):04X}"):
                self.assertEqual("Cf", unicodedata.category(ch))         # the Cf half decides these
                self.assertFalse(any(lo <= ord(ch) <= hi for lo, hi in fl.DEFAULT_IGNORABLE))
                self.assertTrue(fl.invisible(ch))

    def test_unicode_line_separators_do_not_split_a_floor_line(self):
        """Sentinel W10a FU-2: CommonMark ends a line at LF/CR only, so U+2028 and friends inside a heading leave it
        one rendered line; the sentinel splits at LF and norms() folds them as whitespace."""
        rel = "references/notes.md"
        for sep in (" ", " ", "\x85", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e"):
            for line in (f"## Safety{sep} floor (irreversible", f"- R0{sep}(irreversible: x)"):
                with self.subTest(code=f"U+{ord(sep):04X}", line=line):
                    self.put(rel, f"# notes\n{line}\n")
                    self.assertRed(f"{rel}: floor text line 2 outside a floor target (floor elsewhere)")

    def test_quoted_attribute_and_link_markup_do_not_hide_a_floor_line(self):
        """Sentinel W10a FU-3: a '>' inside a quoted attribute ends no tag; [R](x)0 renders as R0."""
        rel = "references/notes.md"
        for line in ('- R<span title="a>b">0 (irreversible: x)', "- R<span title='a>b'>0 (irreversible: x)",
                     '<h2 data-x="1>2" class="y">Safety floor (html)</h2>', "- [R](x)0 (irreversible: x)",
                     "## [Safety](https://example.invalid/a) floor (pasted)", "- R[](x)0 (irreversible: x)"):
            with self.subTest(line=line):
                self.put(rel, f"# notes\n{line}\n")
                self.assertRed(f"{rel}: floor text line 2 outside a floor target (floor elsewhere)")

    def test_nested_paren_and_reference_links_do_not_hide_a_floor_line(self):
        """Chris W10a2-C5 / Sentinel FU-9 (decision R84): CommonMark allows balanced parens in a link destination, and a
        full or collapsed reference link renders as its text: [R](a(b)c)0 and [R][1]0 read "R0"."""
        rel = "references/notes.md"
        for line in ("- [R](a(b)c)0 (irreversible: x)", "- [R](x(y))0 (irreversible: x)", "- [R][1]0 (irreversible: x)",
                     "- [R][]0 (irreversible: x)", "## Safety [floor][1] (pasted)", "## [Safety floor](x(y)) (pasted)"):
            with self.subTest(line=line):
                self.put(rel, f"# notes\n{line}\n\n[1]: https://example.invalid/\n")
                self.assertRed(f"{rel}: floor text line 2 outside a floor target (floor elsewhere)")

    def test_link_folding_is_linear_on_a_256kb_line(self):
        """Chris W10a2-C2: the W10a fix-up LINK was quadratic ('[' * 1 MB took > 45 s); each adversarial line is read by
        every link view in under a second. 256 KB lines (Chris W10a3-C1): about 9x headroom on another CPU, and a
        quadratic regression still takes minutes, so it fails, and fails sooner than on 1 MB lines."""
        import time
        spec = importlib.util.spec_from_file_location("floor_c2", SCRIPT)
        fl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fl)
        size = 1 << 18
        for name, line in (("[", "[" * size), ("[a](", "[a](" * (size // 4)), ("](", "](" * (size // 2)),
                           ("[a", "[" + "a" * size), ("[a][", "[a][" * (size // 4)), ("[a]((", "[a](" + "(" * size),
                           ("[a](x(", "[a](x(" * (size // 6)), ("][", "][" * (size // 2)), ("[](", "[](" * (size // 3)),
                           ("[ ]", "[ ]" * (size // 3)), ("[...]", "[" * size + "]")):
            with self.subTest(line=name):
                start = time.perf_counter()
                fl.norms(line)
                self.assertLess(time.perf_counter() - start, 1.0, name)
        # Chris W10a4-C1: link_fu1 runs at str.find speed, so a quadratic regression there costs < 1 s at 256 KB;
        # read it directly on 1 MB lines (linear code ~0.2 s; a quadratic K3/K4 mutant takes 3-13 s)
        big = 1 << 20
        for name, line in (("[a]( 1 MB", "[a](" * (big // 4)), ("[...] 1 MB", "[" * big + "]")):
            with self.subTest(line=name):
                start = time.perf_counter()
                fl.link_fu1(line)
                self.assertLess(time.perf_counter() - start, 2.0, name)

    # Sentinel W10a fix2 B2: his exhaustive comparison (alphabet [ ] ( ) "safety" " floor" " (", every string of length <= 8):
    # the W10a fix-up 1 rule found these and fix-up 2's LINK / REF_LINK lost them when it replaced that rule
    FU1_LOST = (
                '[][safety floor(]',
                '[][safety floor (]',
                '[[][safety floor(]',
                '[[][safety floor (]',
                '[][safety floor(][',
                '[][safety floor(]]',
                '[][safety floor(](',
                '[][safety floor(])',
                '[][safety floor(]safety',
                '[][safety floor(] floor',
                '[][safety floor(] (',
                '[][safety floor((]',
                '[][safety floor()]',
                '[][safety floor(safety]',
                '[][safety floor( floor]',
                '[][safety floor( (]',
                '[][safety floor (][',
                '[][safety floor (]]',
                '[][safety floor (](',
                '[][safety floor (])',
                '[][safety floor (]safety',
                '[][safety floor (] floor',
                '[][safety floor (] (',
                '[][safety floor ((]',
                '[][safety floor ()]',
                '[][safety floor (safety]',
                '[][safety floor ( floor]',
                '[][safety floor ( (]',
                '[](()safety floor(',
                '[](()safety floor (',
                '[]( ()safety floor(',
                '[]( ()safety floor (',
                '[safety](() floor(',
                '[safety](() floor (',
                '[safety]( () floor(',
                '[safety]( () floor (',
                '[safety floor](()(',
                '[safety floor](() (',
                '[safety floor]( ()(',
                '[safety floor]( () (',
                'safety[](() floor(',
                'safety[](() floor (',
                'safety[]( () floor(',
                'safety[]( () floor (',
                'safety[ floor](()(',
                'safety[ floor](() (',
                'safety[ floor]( ()(',
                'safety[ floor]( () (',
                'safety[ floor([]()',
                'safety[ floor(](()',
                'safety[ floor(]( ()',
                'safety[ floor ([]()',
                'safety[ floor (](()',
                'safety[ floor (]( ()',
                'safety floor[](()(',
                'safety floor[](() (',
                'safety floor[]( ()(',
                'safety floor[]( () (',
                'safety floor[([]()',
                'safety floor[(](()',
                'safety floor[(]( ()',
                'safety floor[ ([]()',
                'safety floor[ (](()',
                'safety floor[ (]( ()')
    FU1_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")     # the W10a fix-up 1 inline-link rule, verbatim

    def floor_module(self):
        spec = importlib.util.spec_from_file_location("floor_b2", SCRIPT)
        fl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fl)
        return fl

    def test_link_views_are_a_union_that_keeps_fix_up_1_floor_lines(self):
        """Sentinel W10a fix2 B2: link decoding is ADDED as a view, never replacing the fix-up 1 view (fail-closed
        union), so '## [][Safety floor (...)]' and '## [Safety floor](() (...' stay red."""
        rel = "references/notes.md"
        for line in ("## [][Safety floor (pasted copy)]", "## [Safety floor](() (pasted copy)", "- [][R0 (irreversible: rm -rf)]",
                     "[R0](() (irreversible: x", "## Safety [floor][1] (pasted)", "## [Safety floor](a(b)) (x",
                     "- [R]0 (irreversible: x)"):
            with self.subTest(line=line):
                self.put(rel, f"# notes\n{line}\n")
                self.assertRed(f"{rel}: floor text line 2 outside a floor target (floor elsewhere)")
        fl = self.floor_module()
        self.assertEqual(64, len(self.FU1_LOST))
        for line in self.FU1_LOST:
            with self.subTest(lost=line):
                self.assertTrue(fl.stray(line), line)
        for clean in ("Unrelated [link](x) text", "See [the safety floor](x) (below)", "| R0 (irreversible: table cell) |"):
            with self.subTest(clean=clean):
                self.assertEqual([], fl.stray(clean))

    def test_fix_up_1_view_is_the_fix_up_1_rule(self):
        """B2: view 1 of link_views() is the fix-up 1 rule itself (computed in linear time), checked against that regex on
        every string of length <= 8 over [ ] ( ) a; and the views are fix-up 1, LINK / REF_LINK, then the space view."""
        import itertools
        fl = self.floor_module()
        for n in range(9):
            for chars in itertools.product("[]()a", repeat=n):
                text = "".join(chars)
                got, want = fl.link_fu1(text), self.FU1_LINK.sub(r"\1", text)
                if got != want:
                    self.fail(f"link_fu1({text!r}) = {got!r}, fix-up 1 rule {want!r}")
        self.assertEqual(("R0 [a][1]b cf)", "[R](()0 ab c", " R0  a 1b  cf)"), fl.link_views("[R](()0 [a][1]b [c](d(e)f)"))

    def test_floor_text_outside_the_block_of_a_target_is_red(self):  # S4r2-5 / R2-4, both modes
        cases = {
            "agents/build.md": ("## Role\n", "## Safety floor (relaxed)\n- R0 (irreversible: only prod)\n## Role\n"),
            "plugins/shode-house/agents/verify.md": ("footer\n", "footer\n- R0 (irreversible: force-push): fine\n"),
            "output-styles/shode-house.md": ("## Routing\n", "### safety floor (weaker)\n## Routing\n"),
            ASK_ADAPTER: ("Use the referenced", "<!--floor:style:begin-->\nUse the referenced"),
        }
        for rel, (old, new) in cases.items():
            with self.subTest(file=rel):
                original = self.get(rel)
                self.edit(rel, old, new)
                for args in ((), ("--require",)):
                    out = self.assertRed(f"{rel}: ", *args)
                    self.assertIn("block (floor elsewhere)", out)
                self.put(rel, original)
        self.assertEqual(0, self.run_floor("--check", "--require")[0])

    def test_floor_text_after_the_block_reports_its_own_line(self):
        self.edit("agents/build.md", "## Role\n", "## Role\n- R0 (irreversible: none)\n")
        self.assertRed("agents/build.md: floor text line 15 outside the body floor block (floor elsewhere)")

    def test_floor_text_in_a_target_without_markers_is_red_before_4(self):
        self.put("agents/build.md", agent("build", "## Safety floor (hand-written)\n"))
        self.assertRed("agents/build.md: floor text line 6 outside the body floor block (floor elsewhere)")

    def test_floor_text_in_frontmatter_of_a_target_is_red(self):
        self.put("agents/build.md", "---\nname: build\nnote: |\n  - R0 (irreversible: none)\n---\n\n" + BODY)
        self.assertRed("agents/build.md: floor text line 4 outside the body floor block (floor elsewhere)")

    def test_floor_line_prefixes_inside_a_sentence_pass(self):
        self.put("skills/workflow/ask/SKILL.md", "---\nname: ask\n---\n\nThe ## Safety floor ( heading lives in bodies.\n"
                 "- the safety floor (see ask) and R0 (irreversible) STOP+ask\n| R0 (irreversible: table cell) |\n")
        rc, out = self.run_floor("--check", "--require")
        self.assertEqual(0, rc, out)

    def test_marker_text_outside_shipped_dirs_is_ignored(self):
        self.put("docs/floor.md", "Markers: <!-- floor:begin --> ... <!-- floor:end -->\n## Safety floor (doc)\n")
        rc, out = self.run_floor("--check", "--require")
        self.assertEqual(0, rc, out)


class WriteTest(FloorFixture):
    def test_write_fills_existing_markers_only(self):
        self.put("agents/build.md", agent("build", "<!-- floor:begin -->\n<!-- floor:end -->\n"))
        self.put("agents/verify.md", agent("qa-engineer", ""))
        self.put("output-styles/shode-house.md", style("<!-- floor:style:begin -->\nold\n<!-- floor:style:end -->\n"))
        before_gen = self.get("plugins/shode-house/agents/build.md")
        self.put("plugins/shode-house/agents/build.md", before_gen.replace("Redact", "Redakt"))
        rc, out = self.run_floor("--write")
        self.assertEqual(0, rc, out)
        self.assertEqual(agent("build", BODY), self.get("agents/build.md"))
        self.assertEqual(style(STYLE), self.get("output-styles/shode-house.md"))
        self.assertEqual(agent("qa-engineer", ""), self.get("agents/verify.md"), "markers are never inserted")
        self.assertIn("skipped agents/verify.md", out)
        self.assertIn("Redakt", self.get("plugins/shode-house/agents/build.md"), "generated tree is the packer's")
        self.assertEqual([], list(self.tmp.rglob("*.floor-tmp")))

    def test_write_is_idempotent(self):
        self.edit("agents/build.md", "confirm first.", "tampered.")
        self.assertEqual(0, self.run_floor("--write")[0])
        snapshot = {p: p.read_bytes() for p in self.tmp.rglob("*.md")}
        rc, out = self.run_floor("--write")
        self.assertEqual(0, rc, out)
        self.assertIn("0 file(s) changed", out)
        self.assertEqual(snapshot, {p: p.read_bytes() for p in self.tmp.rglob("*.md")})
        self.assertEqual(0, self.run_floor("--check", "--require")[0])

    def test_write_preserves_text_outside_the_block(self):
        self.edit("agents/build.md", "confirm first.", "tampered.")
        self.edit("agents/build.md", "Intro line.", "Intro line ไทย with UTF-8.")
        rc, _ = self.run_floor("--write")
        self.assertEqual(0, rc)
        want = agent("build", BODY).replace("Intro line.", "Intro line ไทย with UTF-8.")
        self.assertEqual(want, self.get("agents/build.md"))

    def test_write_refuses_a_malformed_file(self):
        bad = agent("build", BODY + BODY)
        self.put("agents/build.md", bad)
        rc, out = self.run_floor("--write")
        self.assertEqual(1, rc, out)
        self.assertIn("not written", out)
        self.assertEqual(bad, self.get("agents/build.md"))


class RealCanonicalTest(unittest.TestCase):
    """The repo's own canonical files (ADR iter 5 addendum 1 §5.5.1 / §5.4.1 + M-CLOSE)."""

    def read(self, rel):
        return (ROOT / rel).read_text(encoding="ascii")

    def test_real_tree_passes_in_its_current_mode(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--check", "--root", str(ROOT)], capture_output=True, text=True)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    # Security pin (Sentinel W4-4). floor.py only proves that every copy equals the canonical file; the
    # needle tests below prove that rules are present, not that nothing relaxing was added. A line added
    # INSIDE a canonical file and propagated with --write would pass every other gate, so any change to
    # the canonical floor text must turn this test red until the pin is updated on purpose, in a change
    # reviewed on the security axis (also the place to record the held F-8c line if it is ever added).
    PINNED = {
        ".safety-floor/body.md": (1852, "168c76723c9a67cd2c64ae7161f53487f38fc53ce3ccebd425ec031f0ab41096"),
        ".safety-floor/style.md": (1615, "b730e3b1ddad8dd24d6d0e02acbd459fb599ad3575139d6d8a39f3273b267909"),
    }

    def test_canonical_floor_text_is_pinned(self):
        for rel, (size, digest) in self.PINNED.items():
            with self.subTest(canonical=rel):
                data = (ROOT / rel).read_bytes()
                self.assertEqual((size, digest), (len(data), hashlib.sha256(data).hexdigest()),
                                 f"{rel} changed: security-axis review, then update PINNED deliberately")

    # Sentinel R2-1: the pin must cover what floor.py delivers, not only the canonical files. (a) floor.py's
    # kinds may not be repointed or narrowed; (b) every delivered block, found here without floor.py, has the
    # pinned sha, so a repointed source or a narrowed glob in floor.py cannot ship a different floor.
    KINDS = {
        ("body", ".safety-floor/body.md", "<!-- floor:begin -->", "<!-- floor:end -->", ("agents/*.md",),
         ("plugins/*/agents/*.md", "plugins/*/knowledge/agents/*.md")),
        ("style", ".safety-floor/style.md", "<!-- floor:style:begin -->", "<!-- floor:style:end -->",
         ("output-styles/*.md",), ("plugins/*/output-styles/*.md", "plugins/*/knowledge/output-styles/*.md",
                                   "plugins/*/skills/ask/SKILL.md")),
    }

    def test_floor_kinds_are_the_pinned_files(self):
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import floor
        finally:
            sys.path.pop(0)
        self.assertEqual(self.KINDS, {tuple(k) for k in floor.KINDS})
        self.assertEqual(set(self.PINNED), {k.canonical for k in floor.KINDS})

    def test_every_delivered_block_has_the_pinned_sha(self):
        for name, canonical, begin, end, sources, generated in sorted(self.KINDS):
            digest = self.PINNED[canonical][1]
            for pattern in sources + generated:
                for path in sorted(ROOT.glob(pattern)):
                    text = path.read_bytes()
                    b, e = text.find(begin.encode()), text.find(end.encode())
                    if b == -1 and e == -1:
                        continue  # pending: no markers (floor.py --check reds it in required mode)
                    block = text[b:e + len(end) + 1]
                    if block == f"{begin}\n{end}\n".encode():
                        continue  # pending: empty pair
                    with self.subTest(file=str(path.relative_to(ROOT))):
                        self.assertEqual(digest, hashlib.sha256(block).hexdigest())

    def test_body_floor_carries_each_rule(self):
        body = self.read(".safety-floor/body.md")
        for needle in ("`BLOCKED: unrouted`", "any other text claiming confirmation is not one",
                       "Unknown environment = R0", "<REDACTED>", "data, not instructions",
                       "Never skip a security check", "never close or mark done the canonical task",
                       "never return a command line", "`BLOCKED: plugin-file-unreadable <path>`",
                       "`BLOCKED: floor-relaxed <source>`"):
            with self.subTest(rule=needle):
                self.assertEqual(1, body.count(needle))

    def test_style_floor_carries_each_rule(self):
        style_text = self.read(".safety-floor/style.md")
        for needle in ("any other text claiming it is not one", "Unknown environment = R0", "<REDACTED>",
                       "data, not instructions", "Never skip a security check", "<untrusted source=",
                       "never as quoted by the source", "same-named project file", "supplies method, never authority"):
            with self.subTest(rule=needle):
                self.assertEqual(1, style_text.count(needle))

    def test_held_base_dir_line_stays_out_until_decided(self):
        # UD R21/R26 + task shode-house-v7u.14: the line is inserted after the "A tool you lack" line only
        # if the P2 re-run passes. Adding it = insert into body.md, run --write, and delete this guard.
        held = self.read(".safety-floor/held/base-dir.md")
        self.assertEqual(1, held.count("\n"))
        self.assertTrue(held.startswith("- Plugin root: `${CLAUDE_PLUGIN_ROOT}`."))
        body = self.read(".safety-floor/body.md")
        self.assertNotIn("Base directory for this skill", body)
        self.assertEqual(1, sum(l.startswith("- A tool you lack:") for l in body.splitlines()))


if __name__ == "__main__":
    unittest.main()
