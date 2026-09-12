"""Structural routing regression, not behavioral or host-parity proof.

Role inventory comes from the frozen 3.15 baseline; the entrypoint must route to
every retained role and every declared prerequisite must exist in shipped buckets.
Mutation cases prove that missing knowledge cannot silently pass this check.
"""
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("inventory", ROOT / "tests/test_team_package.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def entry_errors(entry, contents):
    errors = []
    baseline = inventory.required_paths()
    roles = sorted(p for p in baseline if p.startswith("agents/") and p.endswith(".md"))
    skills = {Path(p).parent.name: p for p in contents if p.endswith("/SKILL.md")}
    for role in roles:
        if not re.search(r"\|\s*" + re.escape(Path(role).name) + r"\s*\|", entry):
            errors.append("unrouted: " + role)
        body = contents.get(role, "")
        if not body.strip():
            errors.append("missing role: " + role)
            continue
        match = re.search(r"^skills:\s*(\[.*\])$", body, re.M)
        if not match:
            errors.append("missing prerequisites: " + role)
            continue
        for name in json.loads(match.group(1)):
            path = skills.get(name)
            if not path or not contents[path].strip():
                errors.append("missing prerequisite: " + role + ": " + name)
    # Validate the new entry's literal relative resource pointers.
    for relative in re.findall(r"`(\.\./[^`]+\.md)`", entry):
        path = (ROOT / "skills/workflow/ask" / relative).resolve()
        try:
            key = str(path.relative_to(ROOT))
        except ValueError:
            errors.append("escaped plugin root: " + relative)
            continue
        if key not in contents:
            errors.append("broken entry reference: " + relative)
    return errors


class TeamEntryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contents = {
            str(p.relative_to(ROOT)): p.read_text()
            for base in [ROOT / "agents", *[ROOT / "skills" / b for b in inventory.BUCKETS]]
            for p in base.rglob("*.md")
        }
        cls.entry = cls.contents["skills/workflow/ask/SKILL.md"]

    def test_all_baseline_roles_and_prerequisites_reachable(self):
        self.assertEqual([], entry_errors(self.entry, self.contents))

    def test_missing_domain_route_is_detected(self):
        mutated = self.entry.replace("| fintech-expert.md |", "| absent.md |")
        self.assertIn("unrouted: agents/fintech-expert.md", entry_errors(mutated, self.contents))

    def test_missing_domain_knowledge_is_detected(self):
        mutated = dict(self.contents)
        mutated["agents/booking-expert.md"] = ""
        self.assertIn("missing role: agents/booking-expert.md", entry_errors(self.entry, mutated))

    def test_missing_prerequisite_is_detected(self):
        mutated = dict(self.contents)
        mutated.pop("skills/discipline/domain-core/SKILL.md")
        self.assertTrue(any("missing prerequisite:" in e for e in entry_errors(self.entry, mutated)))

    HARNESS_INVARIANTS = (
        "Iteration cap: three review",
        "no user channel exists",
        "mark the task BLOCKED",
        "Do not decide business policy, widen scope or add",
        "Amending an acceptance criterion is the requirements owner's call",
        "never end the\nturn with workers still running",
    )

    def harness_missing(self, text):
        return [f for f in self.HARNESS_INVARIANTS if f not in text]

    def test_harness_unattended_invariants_present(self):
        harness = self.contents["skills/discipline/shode-house-workflow/harness.md"]
        self.assertEqual([], self.harness_missing(harness))

    def test_harness_invariant_removal_is_detected(self):
        harness = self.contents["skills/discipline/shode-house-workflow/harness.md"]
        start = harness.index("Iteration cap:")
        mutated = harness[:start] + harness[harness.index("\n\n", start) + 2:]
        self.assertTrue(self.harness_missing(mutated))

    def test_broken_entry_reference_is_detected(self):
        mutated = self.entry.replace("engineering-loop.md", "does-not-exist.md")
        self.assertTrue(any("broken entry reference:" in e for e in entry_errors(mutated, self.contents)))


if __name__ == "__main__":
    unittest.main()
