#!/usr/bin/env python3
"""Permanent tombstone gate for retired skill names (v3.17 FR-M-1 / Sentinel C3, G-C5).

v3.17 merged 24 -> 20 skills with NO stub: a retired name must not survive anywhere on the shipped or
maintainer surface, or an agent follows a pointer to a skill that no longer exists. The retired list
lives in ONE place -- RETIRED in tests/test_team_package.py -- and every pattern is derived from it.

Allowlist (fixed): CHANGELOG.md (not scanned) - a retired name directly preceded by `formerly ` / `formerly the ` (one line per new owner; the
word elsewhere on the line does not excuse a pointer) -
a line carrying the `tombstone-allow` marker - the `source` / `old_fragment` values of
.rule-migrations.json (exact quotes of baseline text the conservation gate needs; `replacement`,
`requires` and `reason` ARE scanned, so a migration can never point at a retired name).
Not scanned: files pinned by eval/FREEZE.sha256 (frozen probe protocol `probe-freeze-3.17`: they are
hash-locked, so a hit there could never be fixed; they were verified to reference `ask`, not a retired
skill, when the freeze was cut).
Run: python3 tests/test_tombstone.py   (CI gate #11 runs it; also collected by pytest)
"""
import json, pathlib, re, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_team_package import RETIRED  # noqa: E402  (the single retired-names list)

SCAN = (
    "agents", "commands", "output-styles", "skills/workflow", "skills/ops", "skills/ui", "skills/style",
    "skills/discipline", "references", "hooks", "scripts", "tests", "eval/fixtures", "eval/scenarios",
    "eval/prompts", ".github", ".enforcement-map.json", ".rule-migrations.json", ".preload-budget",
    ".skill-metadata-budget", ".agent-core-budget", ".workflow-scenario-budget", ".claude-plugin",
    ".cursor-plugin", "plugins/shode-house", "Makefile", "README.md", "CLAUDE.md", "AGENTS.md",
    "docs/enforcement-map.md", "docs/bd-quickstart.md",
)
MARKER = "tombstone-allow"
FORMERLY = re.compile(r"formerly (the )?$")   # must sit directly before the retired name (Quinn M-1)


def pattern(retired=RETIRED):
    parts = []
    for path in retired:
        _, bucket, name, _ = path.split("/")
        n = re.escape(name)
        parts += [rf"skills/{bucket}/{n}(?![a-z0-9-])", rf"/shode-house:{n}(?![a-z0-9-])", rf"`{n}`", rf"(?<![A-Za-z0-9_-]){n} skill"]
        if name.startswith("shode-house-"):  # a prefixed name is unambiguous even when bare
            parts.append(rf"(?<![A-Za-z0-9_/.-]){n}(?![a-z0-9-])")
    return re.compile("|".join(parts))


def frozen(root):
    sums = root / "eval" / "FREEZE.sha256"
    return {l.split(None, 1)[1].strip().lstrip("*") for l in sums.read_text().splitlines() if l.strip()} if sums.is_file() else set()


def scan(root=ROOT, retired=RETIRED):
    pat, skip, hits = pattern(retired), frozen(root), []
    for entry in SCAN:
        base = root / entry
        files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file()) if base.is_dir() else []
        for f in files:
            rel = f.relative_to(root).as_posix()
            if rel in skip or "__pycache__" in f.parts:
                continue
            try:
                text = f.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            if rel == ".rule-migrations.json":
                data = json.loads(text)
                for item in data.get("migrations", []):
                    item.pop("source", None); item.pop("old_fragment", None)
                text = json.dumps(data, ensure_ascii=False, indent=1)
            hits += [f"{rel}:{i}: {line.strip()[:120]}" for i, line in enumerate(text.splitlines(), 1)
                     if MARKER not in line and any(not FORMERLY.search(line[:m.start()]) for m in pat.finditer(line))]
    return hits


class TombstoneTest(unittest.TestCase):
    def test_retired_dirs_are_gone_and_replacements_exist(self):
        for old, new in RETIRED.items():
            self.assertFalse((ROOT / old).parent.exists(), f"retired skill dir still present: {old}")
            self.assertTrue((ROOT / new).is_file(), f"replacement owner missing: {new}")

    def test_no_retired_name_on_the_scanned_surface(self):
        self.assertEqual([], scan())

    def test_negative_each_retired_name_is_caught(self):
        names = [p.split("/")[2] for p in RETIRED]
        bare = [n for n in names if not n.startswith("shode-house-")]
        self.assertTrue(bare, "negative test needs the un-prefixed retired name")
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); (root / "agents").mkdir()
            lines = [f"load `{n}` first" for n in names]                      # backticked (bare name included)
            lines += [f"see the {n} skill" for n in bare] + [f"run /shode-house:{n}" for n in bare]
            lines += [f"per {n} rules" for n in names if n not in bare]      # bare prefixed name
            lines += [f"read skills/{p.split('/')[1]}/{p.split('/')[2]}/SKILL.md" for p in RETIRED]
            (root / "agents" / "x.md").write_text("\n".join(lines) + "\n")
            self.assertEqual(len(lines), len(scan(root)))
            allowed = [f"formerly `{bare[0]}`", f"`{bare[0]}`  # tombstone-allow", f"a {bare[0]} with the client", "shode-house-driftwood"]
            (root / "agents" / "x.md").write_text("\n".join(allowed) + "\n")
            self.assertEqual([], scan(root))
            # Quinn M-1: "formerly" somewhere on the line is not an escape; it must introduce the name
            (root / "agents" / "x.md").write_text(f"Users formerly confused: run /shode-house:{bare[0]}\n")
            self.assertEqual(1, len(scan(root)))


if __name__ == "__main__":
    if sys.argv[1:] == ["--scan"]:
        found = scan()
        print("\n".join(found)); sys.exit(1 if found else 0)
    unittest.main()
