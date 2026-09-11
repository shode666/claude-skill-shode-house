#!/usr/bin/env python3
"""Maintainer-only: normalize one captured codex exec --json invocation.

Explicit trial identity groups resumed invocations, never unrelated trials.
Incomplete streams remain unscorable. No raw prompts or tool output are exported.
"""
import argparse
import hashlib
import json
from pathlib import Path


def count(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"invalid nonnegative integer: {name}")
    return value


def collect(raw, metadata):
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    required = ("run_id", "invocation_id", "plugin_version", "model", "scenario",
                "source_revision", "source_sha256", "fixture_sha256", "host_version")
    for key in required:
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"missing {key}")
        if metadata[key].lower() in ("unknown", "unavailable"):
            raise ValueError(f"unresolved {key}")
    for key in ("source_sha256", "fixture_sha256"):
        if len(metadata[key]) != 64 or any(c not in "0123456789abcdef" for c in metadata[key]):
            raise ValueError(f"invalid {key}")
    duration = count(metadata.get("duration_ms"), "duration_ms")
    if not isinstance(metadata.get("settings"), dict):
        raise ValueError("settings must record invocation settings")
    if metadata.get("coverage") not in ("main-only", "whole-workflow-no-subagents"):
        raise ValueError("unsupported coverage; child usage needs separate evidence")
    events = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    if not events or any(not isinstance(e, dict) for e in events):
        raise ValueError("invalid or empty event stream")
    threads = [e.get("thread_id") for e in events if e.get("type") == "thread.started"]
    if len(threads) != 1 or not isinstance(threads[0], str) or not threads[0]:
        raise ValueError("expected one thread identity")
    started = 0
    totals = dict(input_tokens=0, cache_read_tokens=0, cache_write_tokens=0, output_tokens=0)
    turns = 0
    for event in events:
        kind = event.get("type")
        if kind in ("error", "turn.failed"):
            raise ValueError("failed stream: retain raw evidence, do not report complete cost")
        if kind == "turn.started":
            if started:
                raise ValueError("overlapping turns")
            started = 1
        elif kind == "turn.completed":
            if not started:
                raise ValueError("completion without start or duplicate completion")
            usage = event.get("usage", {})
            if not isinstance(usage, dict):
                raise ValueError("usage must be an object")
            inp = count(usage.get("input_tokens"), "input_tokens")
            cached = count(usage.get("cached_input_tokens"), "cached_input_tokens")
            written = count(usage.get("cache_write_input_tokens", 0), "cache_write_input_tokens")
            output = count(usage.get("output_tokens"), "output_tokens")
            # This adapter supports observed zero-cache-write Codex CLI streams.
            # Do not guess future nonzero cache-write accounting semantics.
            if written or cached > inp:
                raise ValueError("unsupported cache accounting")
            totals["input_tokens"] += inp - cached
            totals["cache_read_tokens"] += cached
            totals["output_tokens"] += output
            started = 0
            turns += 1
    if started or not turns or events[-1].get("type") != "turn.completed":
        raise ValueError("incomplete stream")
    return {**metadata, **totals, "phase": metadata["scenario"], "command": "ask",
            "agent": "main", "duration_ms": duration, "turns": turns,
            "source_thread_id": threads[0], "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "collector": "codex-json-v1", "usage_complete": True,
            "quality_verdict": "NOT-EVALUATED"}


def save(record, destination):
    """One immutable record per invocation; identical re-ingestion is a no-op."""
    destination.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256(record["invocation_id"].encode()).hexdigest()
    path = destination / f"{identity}.json"
    # Refuse assigning an already-ingested source to a second trial/invocation.
    for prior in destination.glob("*.json"):
        old = json.loads(prior.read_text())
        if not isinstance(old, dict):
            raise ValueError("invalid existing usage record")
        if (old.get("source_thread_id") == record["source_thread_id"]
                and old.get("run_id") != record["run_id"]):
            raise ValueError("resumed thread cannot become an independent trial")
        if old.get("raw_sha256") == record["raw_sha256"] and old != record:
            raise ValueError("source already ingested with different metadata")
    content = json.dumps(record, indent=2, sort_keys=True) + "\n"
    try:
        with path.open("x") as stream:
            stream.write(content)
    except FileExistsError:
        if path.read_text() != content:
            raise ValueError("invocation identity collision")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = collect(args.transcript.read_bytes(), json.loads(args.metadata.read_text()))
        print(save(result, args.out))
    except (ValueError, OSError) as error:
        parser.exit(2, f"UNSCORABLE: {error}\n")
