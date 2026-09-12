"""Maintainer-only recovery guard; never required by the installed plugin.

Freeze the shipped knowledge inventory from the actual 3.15 commit, not from
the candidate packager. This checks preservation, NOT behavioral equivalence.
Intentional relocations/consolidations need an explicit reviewed migration test.
Usage: python3 tests/test_team_package.py path/to/candidate.plugin
"""

import pathlib
import subprocess
import sys
import zipfile


BASELINE = "c67f7e3bff52e5357b5238d205d60070a6ea4ab4"
ROOT = pathlib.Path(__file__).resolve().parents[1]
BUCKETS = ("workflow", "ops", "ui", "style", "discipline")


def required_paths():
    roots = ["agents", "references", "output-styles"]
    roots.extend("skills/" + bucket for bucket in BUCKETS)
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", BASELINE, "--", *roots],
        cwd=ROOT, check=True, text=True, capture_output=True,
    )
    paths = set(result.stdout.splitlines())
    agents = {p for p in paths if p.startswith("agents/") and p.endswith(".md")}
    skills = {p for p in paths if p.endswith("/SKILL.md")}
    if len(agents) != 19 or len(skills) != 23:
        raise RuntimeError("Recovery baseline inventory is invalid")
    return paths


def check(package):
    required = required_paths()
    with zipfile.ZipFile(package) as archive:
        files = {item.filename: item for item in archive.infolist() if not item.is_dir()}
        missing = sorted(required - files.keys())
        empty = sorted(p for p in required & files.keys() if files[p].file_size == 0)
        mismatched = []
        # Reading every required member checks its CRC as well as presence.
        for path in required & files.keys():
            if archive.read(path) != (ROOT / path).read_bytes():
                mismatched.append(path)
    if missing or empty or mismatched:
        print("FAIL: team capability sources missing or empty")
        for path in missing:
            print("  missing:", path)
        for path in empty:
            print("  empty:", path)
        for path in sorted(mismatched):
            print("  differs from candidate source:", path)
        return 1
    print(f"PASS: 19 agents, 23 skills; {len(required)} baseline paths match candidate source bytes")
    print("NOT VERIFIED: delegation behavior, skill reachability, host parity or safety")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 tests/test_team_package.py candidate.plugin")
    sys.exit(check(sys.argv[1]))
