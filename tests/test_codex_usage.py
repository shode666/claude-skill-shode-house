import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("collector", Path(__file__).resolve().parents[1] / "scripts/usage-from-codex.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class CodexUsageTests(unittest.TestCase):
    def setUp(self):
        self.meta = dict(run_id="trial-1", invocation_id="inv-1", plugin_version="3.16-rc",
                         model="observed-model", scenario="review", source_revision="abc",
                         source_sha256="a" * 64, fixture_sha256="b" * 64, host_version="0.153.4",
                         duration_ms=100, settings={}, coverage="whole-workflow-no-subagents")
        self.events = [{"type": "thread.started", "thread_id": "test-thread"},
                       {"type": "turn.started"}, {"type": "turn.completed", "usage":
                        dict(input_tokens=100, cached_input_tokens=80, output_tokens=10)}]

    def collect(self, events=None, meta=None):
        raw = "\n".join(json.dumps(e) for e in (self.events if events is None else events)).encode()
        return collector.collect(raw, self.meta if meta is None else meta)

    def test_disjoint_buckets(self):
        record = self.collect()
        self.assertEqual(record["input_tokens"], 20)
        self.assertEqual(record["cache_read_tokens"], 80)
        self.assertEqual(record["output_tokens"], 10)
        self.assertEqual(record["quality_verdict"], "NOT-EVALUATED")

    def test_missing_unknown_or_invalid_provenance(self):
        for key in self.meta:
            data = copy.deepcopy(self.meta)
            data.pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.collect(meta=data)
        for model in ("unknown", "", None):
            with self.assertRaises(ValueError):
                self.collect(meta={**self.meta, "model": model})

    def test_incomplete_failed_duplicate_and_malformed(self):
        for events in ([], self.events[:-1], self.events + [self.events[-1]],
                       self.events + [{"type": "turn.failed"}], self.events[1:]):
            with self.subTest(events=events), self.assertRaises(ValueError):
                self.collect(events)
        with self.assertRaises(ValueError):
            collector.collect(b"not JSON", self.meta)
        with self.assertRaises(ValueError):
            self.collect(meta=[])
        events = copy.deepcopy(self.events)
        events[-1]["usage"] = []
        with self.assertRaises(ValueError):
            self.collect(events)

    def test_bad_counters_and_unknown_cache_semantics(self):
        for key, value in (("input_tokens", True), ("output_tokens", -1),
                           ("cached_input_tokens", 101), ("cache_write_input_tokens", 1)):
            events = copy.deepcopy(self.events)
            events[-1]["usage"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.collect(events)

    def test_multiple_turns_sum_not_last_only(self):
        record = self.collect(self.events + self.events[1:])
        self.assertEqual(record["input_tokens"], 40)
        self.assertEqual(record["turns"], 2)

    def test_idempotence_and_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            record = self.collect()
            path = collector.save(record, out)
            self.assertEqual(collector.save(record, out), path)
            self.assertEqual(len(list(out.iterdir())), 1)
            for change in ({"invocation_id": "inv-2", "run_id": "trial-2"},
                           {"invocation_id": "inv-2", "run_id": "trial-2", "raw_sha256": "changed"},
                           {"raw_sha256": "different", "input_tokens": 30}):
                with self.assertRaises(ValueError):
                    collector.save({**record, **change}, out)


if __name__ == "__main__":
    unittest.main()
