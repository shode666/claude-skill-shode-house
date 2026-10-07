#!/usr/bin/env python3
"""Harness instrumentation hook (PreToolUse on the spawn tool; PostToolUse on the spawn tool, Bash, Edit, Write).

Records the fixture's working-tree state after each such call together with the calling thread's agent id, so a
file change can be attributed to the thread and tool call that made it. Silent, always exit 0: it must never influence the run.
Env: SHAPE_SNAP_FILE = JSONL file to append to (outside the fixture).
"""
import hashlib, json, os, subprocess, sys, time

try:
    event = json.load(sys.stdin)
except Exception:
    event = {}
try:
    cwd = event.get("cwd") or os.getcwd()
    top = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or cwd
    status = subprocess.run(["git", "-C", top, "status", "--porcelain", "-uall"], capture_output=True, text=True).stdout
    files = {}
    for line in status.splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        try:
            files[path] = hashlib.sha256(open(os.path.join(top, path), "rb").read()).hexdigest()[:16]
        except OSError:
            files[path] = "deleted"
    head = subprocess.run(["git", "-C", top, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    rec = {"ts": time.time(), "event": event.get("hook_event_name"), "tool": event.get("tool_name"),
           "tool_use_id": event.get("tool_use_id"), "agent_id": event.get("agent_id"),
           "subagent_type": (event.get("tool_input") or {}).get("subagent_type"), "head": head, "files": files}
    with open(os.environ["SHAPE_SNAP_FILE"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
except Exception:
    pass
sys.exit(0)
