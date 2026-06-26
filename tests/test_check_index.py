"""Tests for scripts/check_index.py — one fixture per CLAUDE.md invariant.

Every Cowork-critical rule has a good case (returns 0) and a bad case
(returns 1). These tests ARE the proof the enforcement layer still works.
"""
from __future__ import annotations

import json

import check_index as ci


# ---- #4 Cowork description constraints (_check_text core) ----

def test_check_text_ascii_ok():
    assert ci._check_text("d", "plain ascii ok", 200) == 0


def test_check_text_too_long():
    assert ci._check_text("d", "x" * 201, 200) == 1


def test_check_text_em_dash_forbidden():
    assert ci._check_text("d", "uses an em-dash — here", 200) == 1


def test_check_text_thai_forbidden():
    assert ci._check_text("d", "has thai ส here", 200) == 1


def test_cowork_constraints_good(plugin_tree):
    assert ci.check_cowork_constraints(plugin_tree()) == 0


def test_cowork_constraints_long_desc_fails(plugin_tree):
    root = plugin_tree(plugin_overrides={"description": "x" * 201})
    assert ci.check_cowork_constraints(root) == 1


def test_cowork_constraints_emdash_fails(plugin_tree):
    # The actual v3.1.0 bug: em-dash in description.
    root = plugin_tree(plugin_overrides={"description": "multi-agent team — 19 agents"})
    assert ci.check_cowork_constraints(root) == 1


def test_cowork_marketplace_plugin_desc_over_100_fails(plugin_tree):
    root = plugin_tree(
        marketplace_overrides={"plugins": [{"name": "x", "description": "y" * 101}]}
    )
    assert ci.check_cowork_constraints(root) == 1


# ---- #1 Skill size ----

def test_size_ok(plugin_tree):
    assert ci.check_size(plugin_tree()) == 0


def test_size_over_limit_fails(plugin_tree, monkeypatch):
    # A non-thin-entry skill over MAX_LINES must fail.
    monkeypatch.setattr(ci, "MAX_LINES", 5)
    root = plugin_tree(skills={"workflow": {"diagnose": {"lines": 50}}})
    assert ci.check_size(root) == 1


def test_size_thin_entry_exception(plugin_tree, monkeypatch):
    # 'meeting' is whitelisted: oversize is a warning, not a failure.
    monkeypatch.setattr(ci, "MAX_LINES", 5)
    root = plugin_tree(skills={"workflow": {"meeting": {"lines": 50}}})
    assert ci.check_size(root) == 0


# ---- #6 Agent model frontmatter ----

def test_agent_model_allowed(plugin_tree):
    assert ci.check_agent_models(plugin_tree(agents={"developer": "sonnet"})) == 0


def test_agent_model_dated_string_fails(plugin_tree):
    root = plugin_tree(agents={"developer": "claude-sonnet-4-6"})
    assert ci.check_agent_models(root) == 1


def test_agent_model_fable5_whitelist_fails(plugin_tree):
    # developer is NOT in the Fable-5 whitelist.
    root = plugin_tree(agents={"developer": "claude-fable-5"})
    assert ci.check_agent_models(root) == 1


def test_agent_model_fable5_whitelisted_ok(plugin_tree):
    root = plugin_tree(agents={"staff-engineer": "claude-fable-5"})
    assert ci.check_agent_models(root) == 0


# ---- #8 Manifest array form (the missing rule, bd-103) ----

def test_array_form_good(plugin_tree):
    assert ci.check_manifest_array_form(plugin_tree()) == 0


def test_array_form_object_entries_fail(plugin_tree):
    # The exact v3.1.0 schema-reject bug: array of objects, not strings.
    root = plugin_tree(
        plugin_overrides={"skills": [{"name": "meeting", "path": "skills/workflow/meeting"}]}
    )
    assert ci.check_manifest_array_form(root) == 1


def test_array_form_missing_dot_slash_fails(plugin_tree):
    root = plugin_tree(plugin_overrides={"skills": ["skills/workflow/"]})
    assert ci.check_manifest_array_form(root) == 1


def test_array_form_parent_traversal_fails(plugin_tree):
    root = plugin_tree(plugin_overrides={"skills": ["./../skills/workflow/"]})
    assert ci.check_manifest_array_form(root) == 1


def test_array_form_backslash_fails(plugin_tree):
    root = plugin_tree(plugin_overrides={"skills": ["./skills\\workflow\\"]})
    assert ci.check_manifest_array_form(root) == 1


# ---- repo self-check: the real repo must pass everything ----

def test_real_repo_passes(repo_root_path):
    assert ci.main.__module__  # importable
    # Drive each pure check against the real tree.
    txt = (repo_root_path / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    assert ci.check_size(repo_root_path) == 0
    assert ci.check_excluded(repo_root_path, txt) == 0
    assert ci.check_buckets_listed(repo_root_path, txt) == 0
    assert ci.check_cowork_constraints(repo_root_path) == 0
    assert ci.check_agent_models(repo_root_path) == 0
    assert ci.check_model_table_single_source(repo_root_path) == 0
    assert ci.check_manifest_array_form(repo_root_path) == 0
