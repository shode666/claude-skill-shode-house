"""Workflow-level usage regression tests; no host/API calls."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'usage_report', Path(__file__).resolve().parents[1] / 'scripts/usage-report.py')
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a, self.b = [Path(self.tmp.name) / n for n in ('a', 'b')]

    def records(self, root, invocations=1, tokens=100, cache=0, runs=3, scenario='review'):
        directory = root / scenario
        directory.mkdir(parents=True, exist_ok=True)
        for run in range(runs):
            for invocation in range(invocations):
                record = dict(run_id=f'run-{run}', plugin_version='test', model='test',
                              command='review', phase='3b', agent=f'agent-{invocation}',
                              input_tokens=tokens, cache_read_tokens=cache,
                              cache_write_tokens=0, output_tokens=0, duration_ms=1)
                (directory / f'{run}-{invocation}.json').write_text(json.dumps(record))

    def compare(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return usage.compare(str(self.a), str(self.b))

    def test_equal_runs_pass(self):
        self.records(self.a)
        self.records(self.b)
        self.assertEqual(self.compare(), 0)

    def test_more_cheaper_invocations_still_regress(self):
        self.records(self.a, invocations=1, tokens=100)
        self.records(self.b, invocations=3, tokens=80)
        self.assertEqual(self.compare(), 1)  # 240/run, not median 80/invocation

    def test_cache_read_growth_is_visible(self):
        self.records(self.a)
        self.records(self.b, cache=500)
        self.assertEqual(self.compare(), 1)

    def test_zero_baseline_does_not_hide_growth(self):
        self.records(self.a, tokens=0)
        self.records(self.b)
        self.assertEqual(self.compare(), 1)

    def test_missing_directories_are_unscorable(self):
        with self.assertRaises(usage.Unscorable):
            self.compare()

    def test_empty_directories_are_unscorable(self):
        self.a.mkdir()
        self.b.mkdir()
        with self.assertRaises(usage.Unscorable):
            self.compare()

    def test_scenario_mismatch_is_unscorable(self):
        self.records(self.a)
        self.records(self.b, scenario='implement')
        with self.assertRaises(usage.Unscorable):
            self.compare()

    def test_invocations_are_not_independent_runs(self):
        self.records(self.a, invocations=9, runs=1)
        self.records(self.b, invocations=9, runs=1)
        with self.assertRaises(usage.Unscorable):
            self.compare()

    def test_invalid_record_never_silently_skipped(self):
        self.records(self.a)
        self.records(self.b)
        for value in ('{', '[]', '{}'):
            with self.subTest(value=value):
                (self.b / 'review' / 'broken.json').write_text(value)
                with self.assertRaises(usage.Unscorable):
                    self.compare()

    def test_bad_token_values_rejected(self):
        self.records(self.a)
        self.records(self.b)
        path = self.b / 'review' / '0-0.json'
        record = json.loads(path.read_text())
        for value in (True, -1, None, 1.5, '100'):
            with self.subTest(value=value):
                record['input_tokens'] = value
                path.write_text(json.dumps(record))
                with self.assertRaises(usage.Unscorable):
                    self.compare()


if __name__ == '__main__':
    unittest.main()
