#!/usr/bin/env python3
"""Maintainer-only Claude usage observations, NOT complete benchmark records.

Supply one transcript, --metadata JSON and --out. Native completion boundaries,
resumed slices and whole-workflow coverage still require live host validation.
"""
import argparse
import hashlib
import json
from pathlib import Path


def observe(raw, metadata, coverage="main-only"):
    if coverage not in ("main-only", "subagents-only"):
        raise ValueError("unsupported coverage")
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    required = ("run_id", "invocation_id", "plugin_version", "model", "scenario",
                "source_revision", "source_sha256", "fixture_sha256", "host_version")
    for key in required:
        value = metadata.get(key)
        if not isinstance(value, str) or not value.strip() or value.lower() in ("unknown", "unavailable"):
            raise ValueError(f"missing/invalid {key}")
    for key in ("source_sha256", "fixture_sha256"):
        if len(metadata[key]) != 64 or any(c not in "0123456789abcdef" for c in metadata[key]):
            raise ValueError(f"invalid {key}")
    if metadata.get("coverage") != coverage or not isinstance(metadata.get("settings"), dict):
        raise ValueError("matching coverage and settings required")
    fields = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")
    messages, identities = {}, set()
    for line in raw.decode().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("invalid transcript row")
        message = row.get("message")
        if not isinstance(message, dict) or "usage" not in message:
            if "usage" in row:
                raise ValueError("unsupported top-level usage")
            continue
        if row.get("type") != "assistant" or not isinstance(message.get("usage"), dict):
            raise ValueError("unsupported usage row")
        session, message_id = row.get("sessionId"), message.get("id")
        if not all(isinstance(v, str) and v for v in (session, message_id)):
            raise ValueError("native session/message identity required")
        sidechain = row.get("isSidechain", False)
        if type(sidechain) is not bool or sidechain != (coverage == "subagents-only"):
            raise ValueError("mixed or mismatched main/subagent coverage")
        agent = row.get("agentId") if sidechain else "main"
        if not isinstance(agent, str) or not agent:
            raise ValueError("native subagent identity required")
        identities.add((session, agent))
        if len(identities) != 1:
            raise ValueError("mixed sources; collect separately")
        counts = {}
        for key in fields:
            value = message["usage"].get(key)
            if type(value) is not int or value < 0:
                raise ValueError(f"missing/invalid {key}; do not assume zero")
            counts[key] = value
        if message_id in messages and messages[message_id] != counts:
            raise ValueError("conflicting usage snapshots; schema review required")
        messages[message_id] = counts
    if not messages:
        raise ValueError("no identifiable assistant usage")
    session, agent = next(iter(identities))
    provenance = {key: metadata[key] for key in (*required, "coverage", "settings")}
    return {**provenance, "source_session_id": session, "source_agent_id": agent,
            "raw_sha256": hashlib.sha256(raw).hexdigest(), "collector": "claude-observation-v2",
            "observed_usage": {k: sum(u[k] for u in messages.values()) for k in fields},
            "unique_messages": len(messages), "usage_complete": False, "duration_ms": None,
            "quality_verdict": "NOT-EVALUATED", "benchmark_verdict": "UNSCORABLE",
            "limitation": "Completion boundary, resumed slices and whole-workflow coverage unverified"}


def save(record, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (hashlib.sha256(record["invocation_id"].encode()).hexdigest() + ".json")
    for other in directory.glob("*.json"):
        previous = json.loads(other.read_text())
        if not isinstance(previous, dict):
            raise ValueError("invalid existing observation")
        same_source = (previous.get("source_session_id"), previous.get("source_agent_id")) == (record["source_session_id"], record["source_agent_id"])
        if (same_source or previous.get("raw_sha256") == record["raw_sha256"]) and previous != record:
            raise ValueError("source already ingested; overlapping/resumed slices unsupported")
    content = json.dumps(record, indent=2, sort_keys=True) + "\n"
    try:
        with path.open("x") as stream:
            stream.write(content)
    except FileExistsError:
        if path.read_text() != content:
            raise ValueError("invocation identity collision")
    return path


def main(coverage="main-only"):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        record = observe(args.transcript.read_bytes(), json.loads(args.metadata.read_text()), coverage)
        print(save(record, args.out))
        print("OBSERVATION ONLY: UNSCORABLE for whole-workflow benchmarking")
        return 0
    except (ValueError, OSError) as error:
        parser.exit(2, f"UNSCORABLE: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
