import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location("collector", Path(__file__).resolve().parents[1] / "scripts/usage-from-transcript.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class ClaudeObservationTests(unittest.TestCase):
    def setUp(self):
        self.meta = dict(run_id="trial-1", invocation_id="call-1", plugin_version="3.16-rc",
                         model="observed-model", scenario="review", source_revision="abc",
                         source_sha256="a"*64, fixture_sha256="b"*64, host_version="observed",
                         settings={}, coverage="main-only")
        self.row = dict(type="assistant", sessionId="s1", message=dict(id="m1", usage=dict(
            input_tokens=10, cache_read_input_tokens=80, cache_creation_input_tokens=20, output_tokens=5)))

    def observe(self, rows=None, meta=None, coverage="main-only"):
        raw = "\n".join(json.dumps(r) for r in (rows if rows is not None else [self.row])).encode()
        return collector.observe(raw, self.meta if meta is None else meta, coverage)

    def test_partial_and_duplicate_dedup(self):
        record = self.observe([self.row, self.row])
        self.assertEqual(record["unique_messages"], 1)
        self.assertEqual(record["observed_usage"]["input_tokens"], 10)
        self.assertFalse(record["usage_complete"])
        self.assertIsNone(record["duration_ms"])
        self.assertEqual(record["benchmark_verdict"], "UNSCORABLE")
        self.assertNotIn("input_tokens", record)

    def test_provenance_required(self):
        for key in self.meta:
            meta = self.meta.copy()
            del meta[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.observe(meta=meta)

    def test_metadata_cannot_inject_complete_usage(self):
        record = self.observe(meta={**self.meta, "input_tokens": 123,
                                   "duration_ms": 0, "usage_complete": True})
        self.assertNotIn("input_tokens", record)
        self.assertIsNone(record["duration_ms"])
        self.assertFalse(record["usage_complete"])
        with self.assertRaises(ValueError):
            self.observe(meta={**self.meta, "coverage": "full"}, coverage="full")

    def test_cli_coverage_and_malformed_fail_closed(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript, metadata = root / "input.jsonl", root / "meta.json"
            for filename, coverage, sidechain in (
                    ("usage-from-transcript.py", "main-only", False),
                    ("usage-from-cowork.py", "subagents-only", True)):
                row = {**self.row, "isSidechain": sidechain, "agentId": "a1"}
                transcript.write_text(json.dumps(row) + "\n")
                metadata.write_text(json.dumps({**self.meta, "coverage": coverage}))
                command = [sys.executable, str(scripts / filename), str(transcript),
                           "--metadata", str(metadata), "--out", str(root / filename)]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("OBSERVATION ONLY", result.stdout)
                transcript.write_text(json.dumps({**row, "isSidechain": not sidechain}))
                self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
                transcript.write_text("malformed\n")
                self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)

    def test_conflicting_snapshots_and_mixed_sources(self):
        other = copy.deepcopy(self.row)
        other["message"]["usage"]["output_tokens"] = 6
        with self.assertRaises(ValueError):
            self.observe([self.row, other])
        with self.assertRaises(ValueError):
            self.observe([self.row, {**self.row, "sessionId": "s2"}])

    def test_malformed_and_invalid_counters(self):
        for raw in (b"bad json", b"[]", b"{}", b'{"usage":{}}'):
            with self.assertRaises(ValueError):
                collector.observe(raw, self.meta)
        for value in (None, True, -1, "1"):
            row = copy.deepcopy(self.row)
            row["message"]["usage"]["input_tokens"] = value
            with self.assertRaises(ValueError):
                self.observe([row])

    def test_missing_native_identity(self):
        for key in ("sessionId", "message"):
            row = copy.deepcopy(self.row)
            del row[key]
            with self.assertRaises(ValueError):
                self.observe([row])

    def test_subagent_explicit_and_separate(self):
        row = {**self.row, "isSidechain": True, "agentId": "a1"}
        with self.assertRaises(ValueError):
            self.observe([row])
        meta = {**self.meta, "coverage": "subagents-only"}
        self.assertEqual(self.observe([row], meta, "subagents-only")["source_agent_id"], "a1")
        with self.assertRaises(ValueError):
            self.observe([row, {**row, "agentId": "a2"}], meta, "subagents-only")

    def test_idempotence_collisions_and_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            record = self.observe()
            path = collector.save(record, out)
            self.assertEqual(collector.save(record, out), path)
            self.assertEqual(len(list(out.glob("*.json"))), 1)
            for change in ({"run_id": "trial-2", "invocation_id": "call-2"},
                           {"raw_sha256": "different", "invocation_id": "call-2"},
                           {"source_session_id": "s2", "raw_sha256": "different"}):
                with self.assertRaises(ValueError):
                    collector.save({**record, **change}, out)


if __name__ == "__main__":
    unittest.main()
