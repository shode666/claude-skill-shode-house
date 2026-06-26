"""Tests for scripts/lint.py — frontmatter + structural checks.

Drives the real lint functions against tmp trees and the real repo.
"""
from __future__ import annotations

import json

import lint


def test_json_syntax_good(plugin_tree):
    assert lint.check_json_syntax(plugin_tree()) == 0


def test_json_syntax_broken_fails(plugin_tree):
    root = plugin_tree()
    (root / ".claude-plugin" / "plugin.json").write_text("{ not valid json ", encoding="utf-8")
    assert lint.check_json_syntax(root) == 1


def test_skill_frontmatter_good(plugin_tree):
    assert lint.check_skill_frontmatter(plugin_tree()) == 0


def test_skill_name_mismatch_fails(plugin_tree):
    root = plugin_tree()
    bad = root / "skills" / "workflow" / "meeting" / "SKILL.md"
    bad.write_text(
        "---\nname: wrong-name\ndescription: x\n---\n# body\n", encoding="utf-8"
    )
    assert lint.check_skill_name_match(root) == 1


def test_agent_frontmatter_good(plugin_tree):
    assert lint.check_agent_frontmatter(plugin_tree()) == 0


def test_real_repo_lint_structural_passes(repo_root_path):
    assert lint.check_json_syntax(repo_root_path) == 0
    assert lint.check_skill_frontmatter(repo_root_path) == 0
    assert lint.check_command_frontmatter(repo_root_path) == 0
    assert lint.check_agent_frontmatter(repo_root_path) == 0
    assert lint.check_skill_name_match(repo_root_path) == 0
    assert lint.check_skill_cross_refs(repo_root_path) == 0
    assert lint.check_path_refs(repo_root_path) == 0
