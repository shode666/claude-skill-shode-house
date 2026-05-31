#!/usr/bin/env python3
"""setup_precommit.py — install pre-commit hook for shode-house contributors.

Cross-platform replacement for scripts/setup-precommit.sh (v3.5+).
Stdlib + system pre-commit CLI.

One-time setup. Run after fresh clone.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import repo_root, red, green, yellow  # noqa: E402


def install_precommit() -> bool:
    """Best-effort install of pre-commit CLI."""
    if shutil.which("brew"):
        yellow("  brew found — installing pre-commit via brew")
        subprocess.run(["brew", "install", "pre-commit"], check=False)
    elif shutil.which("pip"):
        yellow("  pip found — installing pre-commit via pip")
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "pre-commit"], check=False)
    elif shutil.which("pipx"):
        subprocess.run(["pipx", "install", "pre-commit"], check=False)
    else:
        red("  ✗ Neither brew, pip, nor pipx found.")
        print("  Install pre-commit manually: https://pre-commit.com/#install")
        return False
    return shutil.which("pre-commit") is not None


def main() -> int:
    root = repo_root()
    print("==> shode-house — pre-commit setup\n")

    if not shutil.which("pre-commit"):
        print("  pre-commit not found. Installing...")
        if not install_precommit():
            return 1

    ver = subprocess.run(["pre-commit", "--version"], capture_output=True, text=True).stdout.strip()
    green(f"  ✓ pre-commit: {ver}")

    print("\n==> Installing git pre-commit hook")
    subprocess.run(["pre-commit", "install"], cwd=str(root), check=True)
    green("  ✓ hook installed (.git/hooks/pre-commit)")

    print("\n==> Running pre-commit on all files (first pass)")
    res = subprocess.run(["pre-commit", "run", "--all-files"], cwd=str(root), check=False)
    if res.returncode == 0:
        print()
        green("  ✅ All hooks pass — repo is clean")
    else:
        print()
        yellow("  ⚠ Some hooks reported issues. Review output + fix before next commit.")
        print("    Re-run: pre-commit run --all-files")
        return 1

    print("\n==> Setup complete\n")
    print("Now every 'git commit' will run:")
    print("  - check-yaml / check-json / EOF + whitespace fixers")
    print("  - gitleaks (secret scan)")
    print("  - yamllint")
    print("  - shode-house lint.py (8 plugin-specific checks)\n")
    print("To bypass (NOT recommended): git commit --no-verify")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
