#!/usr/bin/env python3
"""Maintainer-only Cowork subagent observations, never whole-workflow usage.

Supply one explicit transcript, --metadata JSON with coverage=subagents-only,
and --out. No automatic selection of latest agents or scenario-derived trial IDs.
"""
import importlib.util
from pathlib import Path

if __name__ == "__main__":
    spec = importlib.util.spec_from_file_location("claude_usage", Path(__file__).with_name("usage-from-transcript.py"))
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    collector.__doc__ = __doc__
    raise SystemExit(collector.main("subagents-only"))
