"""Held-back acceptance test for scenario S3 (SPEC bd-106). Never copied into the fixture before the run.
Run by score.py as: python3 <this file> <fixture-dir>   (exit 0 = all AC hold)."""
import os, sys, unittest

FIXTURE = sys.argv.pop(1)
sys.path.insert(0, os.path.join(FIXTURE, "src"))


class Bd106(unittest.TestCase):
    def setUp(self):
        from durationfmt import format_duration
        self.f = format_duration

    def test_ac1(self):
        self.assertEqual(self.f(5400), "1h30m")

    def test_ac2(self):
        self.assertEqual(self.f(0), "0s")

    def test_ac3(self):
        self.assertEqual(self.f(3600), "1h")
        self.assertEqual(self.f(3661), "1h1m1s")
        self.assertEqual(self.f(59), "59s")
        self.assertEqual(self.f(60), "1m")

    def test_ac4(self):
        for bad in (-1, True, False, 1.5, "60", None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.f(bad)

    def test_ac5(self):
        self.assertEqual(self.f(90000), "25h")
        self.assertEqual(self.f(86400), "24h")


if __name__ == "__main__":
    unittest.main()
