#!/usr/bin/env python3
"""Permanent tracker-neutral gate (v3.17 FR-T-1 AC1/AC2, ticket shode-house-8ss.52).

The tracker follows the TARGET project, so a shipped surface must not hardcode a Beads command
(`bd <verb>`). Task operations are worded with neutral verbs (create / find ready / claim / note /
close + read back / link) against the project's confirmed tracker (harness contract; Markdown fallback).
Allowlist (fixed, ONE file): skills/discipline/shode-house-workflow/harness.md -- its labelled
"Beads example" block. Identifier tokens (`bd-id`, `bd:<id>`, `{bd}`, `bd-42`) are not commands
and do not match. This repo's own maintainer files (AGENTS.md, CLAUDE.md, docs/, scripts/) are not scanned.
Run: python3 tests/test_tracker_neutral.py   (CI gate #11 runs it; also collected by pytest)
"""
import pathlib, re, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN = ("agents", "skills/workflow", "skills/ops", "skills/ui", "skills/style", "skills/discipline",
        "commands", "output-styles", "references")
ALLOW = "skills/discipline/shode-house-workflow/harness.md"
COMMAND = re.compile(r"(^|[^a-z-])bd[ \t]+(ready|show|update|close|create|prime|dep|list|remember|link|init|sync|reopen|blocked"
                     r"|comments?|edit|search|delete|label|graph|note|dolt|export|import|stats|doctor)\b")


def scan(root=ROOT):
    found = []
    for top in SCAN:
        for path in sorted((root / top).rglob("*")):
            rel = path.relative_to(root).as_posix()
            if not path.is_file() or rel == ALLOW:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue  # binary (grep -I)
            found += [f"{rel}:{n}: {line.strip()[:120]}" for n, line in enumerate(lines, 1) if COMMAND.search(line)]
    return found


class TrackerNeutralTest(unittest.TestCase):
    def test_no_hardcoded_tracker_command_on_shipped_surface(self):
        self.assertEqual([], scan())

    def test_allowlisted_file_holds_the_labelled_example(self):
        text = (ROOT / ALLOW).read_text(encoding="utf-8")
        self.assertIn("## Beads example — only when the project's confirmed tracker is Beads", text)

    def test_negative_agent_file_red_harness_green_tokens_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            for top in SCAN:
                (root / top).mkdir(parents=True)
            (root / ALLOW).parent.mkdir(parents=True)
            (root / ALLOW).write_text("bd close <id> && bd show <id>\n")
            self.assertEqual([], scan(root))                                   # harness.md -> green
            (root / "agents" / "x.md").write_text("then bd close <id>\n`bd ready --json`\nbd  close 1\nbd sync\nbd\tshow 1\n")
            self.assertEqual(5, len(scan(root)))                               # agent file -> red
            (root / "agents" / "x.md").write_text("outputs/<bd-id>/ [bd:42] shortcut(bd:7): {bd} abd show per-bd close\n")
            self.assertEqual([], scan(root))                                   # identifier tokens are not commands


if __name__ == "__main__":
    if sys.argv[1:] == ["--scan"]:
        hits = scan()
        print("\n".join(hits)); sys.exit(1 if hits else 0)
    unittest.main()
