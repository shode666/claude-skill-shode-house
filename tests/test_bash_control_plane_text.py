#!/usr/bin/env python3
"""Shipped text never tells an agent to run a Bash command that the C5 control-plane guard denies (U22 H1 follow-up,
bd:shode-house-v7u.4.48 slice C-init).

hooks/scripts/guard-scope-write.sh (C5) denies, in an engaged project, every Bash command that names `.shode-house`
itself or one of its control-plane roots (state, journal, scope). A shipped instruction that still says "run this in
Bash" with such a name breaks the moment the project is engaged: that is what happened to the `/init` Phase 0
`.gitignore` snippet. The sanctioned mutators (scripts/workflow-state.sh, scripts/scope-check.sh) are called by
script name and hold the path only inside the script, so they never match.

What counts as "instructs a Bash command": a fenced block whose info string is a shell language (bash, sh, shell,
zsh, console). The whole block is judged, comments included, because the hook judges the whole command string.
The pattern is read from the hook itself and the normalisation (line breaks to spaces, squeeze runs of "/", drop "/./",
ignore ASCII case) mirrors its pipeline, so this lint does not drift from what the hook denies.
Known limits (not seen, by design, to stay free of false positives): an unlabelled or non-shell fence (a directory
tree, YAML, JSON), an inline code span, and prose such as "run rm on the directory". Those are not runnable text an
agent pastes into Bash as is. Scope = the shipped text surfaces of tests/test_tracker_neutral.py (agents, the five
skill buckets, commands, output-styles, references), Markdown only; the generated plugins/ tree is a copy checked by
CI #25.
Run: python3 tests/test_bash_control_plane_text.py   (CI gate #11 runs it; also collected by pytest)
"""
import pathlib, re, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks/scripts/guard-scope-write.sh"
SCAN = ("agents", "skills/workflow", "skills/ops", "skills/ui", "skills/style", "skills/discipline",
        "commands", "output-styles", "references")
SHELL = {"bash", "sh", "shell", "zsh", "console"}
FENCE = re.compile(r"^\s*(```+|~~~+)\s*([A-Za-z0-9_+-]*)")


def hook_pattern(hook=HOOK):
    """The one ERE the C5 branch passes to `grep -iqE`; exactly one, or the lint cannot say what is denied."""
    found = re.findall(r"grep -iqE '([^']+)'", hook.read_text(encoding="utf-8"))
    if len(found) != 1:
        raise AssertionError(f"{hook}: expected exactly one C5 `grep -iqE '<ERE>'`, found {len(found)}")
    return re.compile(found[0], re.I | re.M)  # grep is line-based; the hook joins lines first (`tr '\n' ' '`)


def denied(text, pattern):
    """Same normalisation as the hook pipeline: `tr -s '/\\n' '/ '` then `sed ':a; s#/\\./#/#g; ta'`."""
    s = re.sub(r" +", " ", re.sub(r"/+", "/", text.replace("\n", " ")))
    while "/./" in s:
        s = s.replace("/./", "/")
    return pattern.search(s) is not None


def shell_blocks(text):
    """(first line number, body) of every shell-labelled fenced block."""
    out, lang, opener, start, body = [], None, None, 0, []
    for n, line in enumerate(text.splitlines(), 1):
        m = FENCE.match(line)
        if opener is None and m:
            opener, lang, start, body = m.group(1), m.group(2).lower(), n, []
        elif opener is not None and line.strip().startswith(opener[0] * len(opener)) and not line.strip().strip(opener[0]):
            if lang in SHELL:
                out.append((start, "\n".join(body)))
            opener = None
        elif opener is not None:
            body.append(line)
    return out


def scan(root=ROOT, hook=HOOK):
    pattern, found = hook_pattern(hook), []
    for top in SCAN:
        for path in sorted((root / top).rglob("*.md")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            for start, body in shell_blocks(path.read_text(encoding="utf-8")):
                if denied(body, pattern):
                    found.append(f"{rel}:{start}: shell block names a Bash-denied control-plane path "
                                 "(use the Read/Edit/Write tool, or scripts/workflow-state.sh / scripts/scope-check.sh)")
    return found


class BashControlPlaneTextTest(unittest.TestCase):
    def test_shipped_text_has_no_denied_bash_block(self):
        self.assertEqual([], scan())

    def test_hook_pattern_is_read_from_the_hook(self):
        p = hook_pattern()
        for cmd in ("rm -rf .shode-house", "mv ./.shode-house//state x", "cat .SHODE-HOUSE/journal/x",
                    "printf '%s\\n' \"/.shode-house/\" >> .gitignore", "ls .shode-house/./scope"):
            self.assertTrue(denied(cmd, p), cmd)
        for cmd in ("scripts/scope-check.sh <bd-id> <agent> <path> --verify", "scripts/workflow-state.sh status x",
                    "cat .shode-house/config.yaml", "cp -f a b.shode-house.new", "ls .shode-house-backup"):
            self.assertFalse(denied(cmd, p), cmd)

    def test_negative_shell_block_red_other_forms_green(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            for top in SCAN:
                (root / top).mkdir(parents=True)
            md = root / "commands" / "x.md"
            md.write_text("```bash\nscripts/scope-check.sh b a p --snapshot\ncat .shode-house/config.yaml\n```\n"
                          "```yaml\nignore: /.shode-house/\n```\n```\n.shode-house/\n```\n"
                          "Use the Edit tool to add `/.shode-house/` to `.gitignore`.\n")
            self.assertEqual([], scan(root))                                  # sanctioned / non-shell -> green
            md.write_text("intro\n```bash\n# rule \".shode-house\"\nRULE=\"/.shode-house/\"\n```\n"
                          "~~~sh\nrm -rf .shode-house/state\n~~~\n````console\n$ ls .shode-house\n````\n")
            self.assertEqual(["commands/x.md:2", "commands/x.md:6", "commands/x.md:9"],
                             [f.split(": ")[0] for f in scan(root)])          # three shell blocks -> red


if __name__ == "__main__":
    if sys.argv[1:] == ["--scan"]:
        hits = scan()
        print("\n".join(hits)); sys.exit(1 if hits else 0)
    unittest.main()
