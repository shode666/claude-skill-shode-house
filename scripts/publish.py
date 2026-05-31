#!/usr/bin/env python3
"""publish.py — version-agnostic publish (commit + push + tag).

Cross-platform replacement for scripts/publish.sh (v3.5+).
Reads VERSION from .claude-plugin/plugin.json automatically.

Sandbox can't run git commit/push — run from real macOS/Linux/Windows terminal.
Idempotent: safe to re-run if any step fails.

Usage::

    python3 scripts/publish.py [--branch main]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import repo_root, red, green  # noqa: E402


def run(cmd: list[str], cwd: Path, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), check=check, capture_output=capture, text=True)


def get_version(root: Path) -> str:
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return plugin["version"]


def extract_changelog(root: Path, version: str) -> str:
    """Extract latest CHANGELOG entry for given version."""
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    in_section = False
    lines: list[str] = []
    for line in changelog.splitlines():
        if line.startswith(f"## [{version}]"):
            in_section = True
            continue
        if line.startswith("## [") and in_section:
            break
        if in_section:
            lines.append(line)
    return "\n".join(lines[:50]).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="main")
    args = ap.parse_args()

    root = repo_root()
    version = get_version(root)
    tag = f"v{version}"

    remote_url = run(["git", "remote", "get-url", "origin"], root, capture=True).stdout.strip()
    current_branch = run(["git", "branch", "--show-current"], root, capture=True).stdout.strip()

    print(f"==> shode-house {tag} publish")
    print(f"    repo:    {remote_url}")
    print(f"    branch:  {current_branch}")
    print(f"    version: {version} (from plugin.json)")
    print()

    # Step 1: clean stale locks
    print("==> Step 1: clean stale .git/index.lock")
    for lock in (".git/index.lock", ".git/HEAD.lock"):
        try:
            (root / lock).unlink()
        except FileNotFoundError:
            pass
    print("    ok\n")

    # Step 2: lint
    print("==> Step 2: scripts/lint.py (8 pre-publish checks)")
    lint = run([sys.executable, "scripts/lint.py"], root, check=False)
    if lint.returncode != 0:
        red("    ✗ LINT FAILED — fix issues before publishing")
        return 1
    print()

    # Step 3: build
    print(f"==> Step 3: rebuild shode-house-{tag}.plugin")
    run([sys.executable, "scripts/build_plugin.py"], root)
    print()

    # Step 4: stage
    print("==> Step 4: stage all changes")
    run(["git", "add", "-A"], root)
    diff_stat = run(["git", "diff", "--cached", "--stat"], root, capture=True).stdout
    if diff_stat:
        print("Staged changes summary:")
        for line in diff_stat.splitlines()[-3:]:
            print(line)
    print()

    # Step 5: commit (skip if nothing staged)
    nothing_staged = run(["git", "diff", "--cached", "--quiet"], root, check=False).returncode == 0
    if nothing_staged:
        print(f"==> Step 5: nothing to commit. Skipping.\n")
    else:
        body = extract_changelog(root, version)
        msg = f"{tag} — see CHANGELOG.md\n\n{body}\n\nSee full CHANGELOG.md for details."
        print(f"==> Step 5: commit {tag}")
        run(["git", "commit", "-m", msg], root)
        print()

    # Step 6: push branch
    print(f"==> Step 6: push {args.branch}")
    run(["git", "push", "origin", args.branch], root)
    print()

    # Step 7: tag (skip if exists)
    print(f"==> Step 7: create tag {tag}")
    existing = run(["git", "tag", "-l", tag], root, capture=True).stdout.strip()
    if existing == tag:
        print(f"    tag {tag} already exists locally — skipping")
    else:
        run(["git", "tag", "-a", tag, "-m", f"{tag} — see CHANGELOG.md for details"], root)
        print(f"    ✓ tag {tag} created")
    print()

    # Step 8: push tag
    print(f"==> Step 8: push tag {tag}")
    run(["git", "push", "origin", tag], root)
    print()

    repo_url = remote_url.removesuffix(".git")
    green(f"==> ✓ {tag} published")
    print(f"    GitHub: {repo_url}/releases/tag/{tag}")
    print()
    print("    Cowork install/update:")
    print("      /plugin marketplace update shode-house")
    print("      /plugin install shode-house@shode-house")
    print()
    print(f"    Or drag-drop: {root}/shode-house-{tag}.plugin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
