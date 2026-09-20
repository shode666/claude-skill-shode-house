"""Negative tests for scripts/rule-conservation.py (v3.17 FR-G-1 / ADR-9.1).

Every case builds a throwaway git repo and runs the real CLI in it, so the git plumbing
(--base, --no-renames, deleted paths) is exercised, not mocked. stdlib + git only.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/rule-conservation.py"

RULE = "Reviewers never approve a deliverable they produced themselves during this release cycle."
ANCHOR = "never approve a deliverable"
FILLER = "Collect the symptom timeline before proposing any hypothesis about the outage."
SKILL = "skills/workflow/alpha/SKILL.md"
OTHER = "skills/ops/beta/SKILL.md"
REF = "skills/workflow/alpha/detail.md"
LAZY = "<!-- lazy-load-contract -->\nLOAD: skills/workflow/alpha/detail.md\n\n"


def doc(*lines):
    return "---\nname: x\ndescription: metadata is not a rule\n---\n# Title\n\n" + "\n".join(lines) + "\n"


class Repo:
    def __init__(self, files):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.git("init", "-q")
        self.write(files)
        self.base = self.commit("base")

    def close(self):
        self._tmp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ("git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false") + args,
            cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def write(self, files):
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def run(self, *args):
        r = subprocess.run((sys.executable, str(SCRIPT)) + args, cwd=self.root, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr


class RuleConservationTest(unittest.TestCase):
    def repo(self, files):
        repo = Repo(files)
        self.addCleanup(repo.close)
        return repo

    def assert_lost(self, result, *needles):
        rc, out = result
        self.assertEqual(1, rc, out)
        self.assertNotIn("Traceback", out)
        for needle in needles:
            self.assertIn(needle, out)

    def assert_ok(self, result):
        rc, out = result
        self.assertEqual(0, rc, out)
        self.assertIn("  ok ", out)

    # AC1 -- --base: a committed loss must still be seen (B1)
    def test_committed_loss_needs_base(self):
        repo = self.repo({SKILL: doc(RULE, FILLER)})
        repo.write({SKILL: doc(FILLER)})
        self.assert_lost(repo.run(), SKILL)            # dirty tree, default HEAD
        repo.commit("drop rule")
        rc, out = repo.run()                            # clean tree vs HEAD: nothing to compare
        self.assertEqual(0, rc, out)
        self.assertIn("no skill/agent file changed", out)
        self.assert_lost(repo.run("--base", repo.base), SKILL, "deliverable")

    def test_unknown_base_fails_closed(self):
        repo = self.repo({SKILL: doc(RULE)})
        rc, out = repo.run("--base", "no-such-ref")
        self.assertEqual(2, rc, out)
        self.assertNotIn("Traceback", out)

    # AC1 / Q2 -- rename detection must not hide the old path
    def test_renamed_skill_is_checked(self):
        repo = self.repo({SKILL: doc(RULE, FILLER)})
        repo.git("mv", "skills/workflow/alpha", "skills/deprecated")
        repo.commit("git mv to deprecated")
        self.assertEqual("skills/deprecated/SKILL.md",          # proof that plain diff hides the old path
                         repo.git("diff", "--name-only", repo.base))
        self.assert_lost(repo.run("--base", repo.base), SKILL, "[file deleted]")

    def test_deprecated_and_in_progress_cannot_hold_a_rule(self):
        repo = self.repo({SKILL: doc(RULE, FILLER)})
        repo.write({SKILL: doc(FILLER), "skills/deprecated/old/SKILL.md": doc(RULE),
                    "skills/in-progress/new/SKILL.md": doc(RULE), "README.md": RULE})
        self.assert_lost(repo.run(), SKILL)

    # AC2 -- deleted file: no crash, rules must live elsewhere (B2)
    def test_deleted_skill_without_destination(self):
        repo = self.repo({SKILL: doc(RULE, FILLER), OTHER: doc(FILLER)})
        (repo.root / SKILL).unlink()
        repo.commit("delete skill")
        self.assert_lost(repo.run("--base", repo.base), SKILL, "[file deleted]", "deliverable")

    def test_deleted_skill_with_rules_merged_elsewhere_passes(self):
        repo = self.repo({SKILL: doc(RULE), OTHER: doc(FILLER)})
        (repo.root / SKILL).unlink()
        repo.write({OTHER: doc(FILLER, "- " + RULE)})
        repo.commit("merge alpha into beta")
        self.assert_ok(repo.run("--base", repo.base))

    # AC3 -- every shipped bucket, reference files and agents (old scope = discipline SKILL.md only)
    def test_all_buckets_references_and_agents_are_in_scope(self):
        paths = [f"skills/{b}/s/SKILL.md" for b in ("workflow", "ops", "ui", "style", "discipline")]
        paths += ["skills/ops/s/runbook.md", "agents/developer.md"]
        for path in paths:
            with self.subTest(path=path):
                repo = self.repo({path: doc(RULE, FILLER)})
                repo.write({path: doc(FILLER)})
                self.assert_lost(repo.run(), path)

    def test_unshipped_and_non_rule_files_are_out_of_scope(self):
        files = {"skills/deprecated/s/SKILL.md": doc(RULE), "skills/in-progress/s/SKILL.md": doc(RULE),
                 "docs/notes.md": doc(RULE)}
        repo = self.repo(files)
        repo.write({path: doc(FILLER) for path in files})
        self.assert_ok(repo.run())

    # AC4 / S7 -- protection does not come from the marker
    def test_unmarked_english_rule_is_protected(self):
        self.assertNotIn("🔴", RULE)
        self.assertNotIn("ห้าม", RULE)
        repo = self.repo({SKILL: doc(RULE, FILLER)})
        repo.write({SKILL: doc(FILLER)})
        self.assert_lost(repo.run(), "deliverable")

    def test_marker_removed_then_line_deleted(self):
        marked = "- 🔴 ห้าม approve deliverable ของตัวเอง reviewer ต้องเป็นคนอื่นเสมอ independent"
        repo = self.repo({SKILL: doc(marked, FILLER)})
        repo.write({SKILL: doc(marked.replace("🔴 ห้าม", "do not"), FILLER)})
        repo.commit("downgrade marker")
        self.assert_ok(repo.run("--base", repo.base))   # rewording alone keeps the rule
        repo.write({SKILL: doc(FILLER)})
        repo.commit("delete the now-unmarked line")
        self.assert_lost(repo.run("--base", repo.base), SKILL)

    def test_noise_bounds(self):
        """Headings, quotes, table rules, short lines, unmarked fenced examples and pointers are not rules."""
        noise = ["## A heading that is long enough to look like a rule line", "> quoted commentary that is long enough to count",
                 "|------|------|------|------|------|", "short line", "```", "example output inside a fenced block only",
                 "```", "See the detailed procedure in skills/workflow/alpha/detail.md before acting"]
        repo = self.repo({SKILL: doc(FILLER, *noise)})
        repo.write({SKILL: doc(FILLER)})
        self.assert_ok(repo.run())

    def test_marked_line_inside_fence_is_still_a_rule(self):
        repo = self.repo({SKILL: doc(FILLER, "```", "🔴 ห้าม deploy production without rollback plan approved", "```")})
        repo.write({SKILL: doc(FILLER)})
        self.assert_lost(repo.run(), "rollback")

    # AC4 / S3 -- tier: a root-only rule may not sink into a lazy reference
    def tier_repo(self, enforcement_map=True):
        files = {SKILL: doc(RULE, FILLER), REF: LAZY + "# Detail\n"}
        if enforcement_map:
            files[".enforcement-map.json"] = json.dumps({"version": 1, "rules": [
                {"id": "reviewer-independence", "root_only": True, "anchor": ANCHOR, "source_of_truth": SKILL},
                {"id": "unrelated", "anchor": "symptom timeline", "source_of_truth": SKILL}]})
        repo = self.repo(files)
        repo.write({SKILL: doc(FILLER), REF: LAZY + "# Detail\n\n" + RULE + "\n"})
        repo.commit("move rule root -> lazy reference")
        return repo

    def test_root_only_rule_moved_to_lazy_reference_fails(self):
        repo = self.tier_repo()
        self.assert_lost(repo.run("--base", repo.base), "root tier", ANCHOR)

    def test_root_only_rule_moved_to_another_root_passes(self):
        repo = self.tier_repo()
        repo.write({"agents/reviewer.md": doc(RULE)})
        self.assert_ok(repo.run("--base", repo.base))

    def test_skill_md_carrying_load_block_is_not_root_tier(self):
        repo = self.tier_repo()
        repo.write({OTHER: LAZY + RULE + "\n"})
        self.assert_lost(repo.run("--base", repo.base), "root tier")

    def test_absent_root_only_list_is_not_an_error(self):
        repo = self.tier_repo(enforcement_map=False)
        self.assert_ok(repo.run("--base", repo.base))   # ordinary rule: a reference may hold it
        self.assert_lost(repo.run("--base", repo.base, "--root-only", ANCHOR), "root tier")

    # .rule-migrations.json semantics preserved
    def migration_repo(self, fragment):
        new = "Producers hand the artifact to an independent gatekeeper who alone signs the verdict."
        repo = self.repo({SKILL: doc(RULE, FILLER), ".rule-migrations.json": json.dumps({"migrations": [{
            "source": SKILL, "old_fragment": fragment, "replacement": SKILL,
            "requires": ["independent gatekeeper"], "reason": "reworded"}]})})
        repo.write({SKILL: doc(new, FILLER)})
        return repo

    def test_exact_migration_exempts_the_fragment(self):
        rc, out = self.migration_repo(RULE).run()
        self.assertEqual(0, rc, out)
        self.assertIn("migrated " + SKILL, out)

    def test_inexact_migration_does_not_exempt(self):
        self.assert_lost(self.migration_repo(RULE[:-1]).run(), "deliverable")

    def test_migration_never_waives_root_tier(self):
        repo = self.migration_repo(RULE)
        self.assert_lost(repo.run("--root-only", ANCHOR), "root tier")


if __name__ == "__main__":
    unittest.main()
