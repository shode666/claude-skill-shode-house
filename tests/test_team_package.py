"""Maintainer-only recovery guard; never required by the installed plugin.

Freeze the shipped knowledge inventory from the actual 3.15 commit, not from
the candidate packager. This checks preservation, NOT behavioral equivalence.
Intentional relocations/consolidations need an explicit reviewed migration test.
Usage: python3 tests/test_team_package.py path/to/candidate.plugin
"""

import pathlib
import subprocess
import sys
import zipfile


BASELINE = "c67f7e3bff52e5357b5238d205d60070a6ea4ab4"
ROOT = pathlib.Path(__file__).resolve().parents[1]
BUCKETS = ("workflow", "ops", "ui", "style", "discipline")
# v3.17 merge 24 -> 20 (no stub). THE single retired-names list: retired baseline path -> file that now
# owns its content. tests/test_tombstone.py (CI gate #11 tombstone) derives its patterns from these keys.
RETIRED = {
    "skills/workflow/meeting/SKILL.md": "skills/workflow/ask/SKILL.md",  # tombstone-allow
    "skills/discipline/shode-house-evidence/SKILL.md": "skills/discipline/shode-house-discipline/SKILL.md",  # tombstone-allow
    "skills/discipline/shode-house-broadcast/SKILL.md": "skills/discipline/shode-house-discipline/handoff.md",  # tombstone-allow
    "skills/discipline/shode-house-drift/SKILL.md": "skills/discipline/shode-house-workflow/drift.md",  # tombstone-allow
    # v4.0.0 switch (ADR iter 5 §5.2/§5.3): the router is the output style; no stub agent, no old style.
    "agents/orchestrator.md": "output-styles/shode-house.md",  # tombstone-allow
    "output-styles/oliver.md": "output-styles/shode-house.md",  # tombstone-allow
    # v4.0.1 consolidation (18 agent types -> 6; shode-house-jni, router decisions R93): no stub agent files. Old id -> the
    # type that owns its work now (the axis / skill / reference is in skills/discipline/shode-house-routing/ownership.md).
    "agents/product-manager.md": "agents/plan.md",  # tombstone-allow
    "agents/business-analyst.md": "agents/plan.md",  # tombstone-allow
    "agents/solution-architect.md": "agents/plan.md",  # tombstone-allow
    "agents/staff-engineer.md": "agents/build.md",  # tombstone-allow
    "agents/developer.md": "agents/build.md",  # tombstone-allow
    "agents/ux-ui-designer.md": "agents/design.md",  # tombstone-allow
    "agents/code-reviewer.md": "agents/verify.md",  # tombstone-allow
    "agents/qa-engineer.md": "agents/verify.md",  # tombstone-allow
    "agents/security-engineer.md": "agents/secure.md",  # tombstone-allow
    "agents/devops-engineer.md": "agents/operate.md",  # tombstone-allow
    "agents/sre-engineer.md": "agents/operate.md",  # tombstone-allow
    "agents/fintech-expert.md": "agents/plan.md",  # tombstone-allow
    "agents/erp-expert.md": "agents/plan.md",  # tombstone-allow
    "agents/sap-expert.md": "agents/plan.md",  # tombstone-allow
    "agents/trading-expert.md": "agents/plan.md",  # tombstone-allow
    "agents/insurance-expert.md": "agents/plan.md",  # tombstone-allow
    "agents/booking-expert.md": "agents/plan.md",  # tombstone-allow
    "agents/ecommerce-expert.md": "agents/plan.md",  # tombstone-allow
}


# v4 W7 (S3): persona-named runbooks renamed with their pointers (UD R9, A6); old path -> new path.
RENAMED = {
    "references/runbooks/oliver-clarify-estimate.md": "references/runbooks/router-clarify-estimate.md",
    "references/runbooks/oliver-engagement.md": "references/runbooks/router-engagement.md",
    "references/runbooks/uma-phase-1b.md": "references/runbooks/design-phase-1b.md",
    "references/runbooks/uma-phase-3a.md": "references/runbooks/design-phase-3a.md",
}


def required_paths():
    roots = ["agents", "references", "output-styles"]
    roots.extend("skills/" + bucket for bucket in BUCKETS)
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", BASELINE, "--", *roots],
        cwd=ROOT, check=True, text=True, capture_output=True,
    )
    paths = set(result.stdout.splitlines())
    agents = {p for p in paths if p.startswith("agents/") and p.endswith(".md")}
    skills = {p for p in paths if p.endswith("/SKILL.md")}
    if len(agents) != 19 or len(skills) != 23:
        raise RuntimeError("Recovery baseline inventory is invalid")
    if not set(RETIRED) <= paths:
        raise RuntimeError("RETIRED names a path that the recovery baseline never shipped")
    # A retired path is replaced, not dropped: its owner must ship, and the old path must NOT.
    return (paths - set(RETIRED) - set(RENAMED)) | set(RETIRED.values()) | set(RENAMED.values())


def check(package):
    required = required_paths()
    with zipfile.ZipFile(package) as archive:
        files = {item.filename: item for item in archive.infolist() if not item.is_dir()}
        missing = sorted(required - files.keys())
        resurrected = sorted(set(RETIRED) & files.keys())
        empty = sorted(p for p in required & files.keys() if files[p].file_size == 0)
        mismatched = []
        # Reading every required member checks its CRC as well as presence.
        for path in required & files.keys():
            if archive.read(path) != (ROOT / path).read_bytes():
                mismatched.append(path)
    if missing or empty or mismatched or resurrected:
        print("FAIL: team capability sources missing or empty")
        for path in resurrected:
            print("  retired path shipped again:", path)
        for path in missing:
            print("  missing:", path)
        for path in empty:
            print("  empty:", path)
        for path in sorted(mismatched):
            print("  differs from candidate source:", path)
        return 1
    print(f"PASS: 19 baseline agents, 23 baseline skills ({len(RETIRED)} retired -> replacement owner present); "
          f"{len(required)} paths match candidate source bytes")
    print("NOT VERIFIED: delegation behavior, skill reachability, host parity or safety")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 tests/test_team_package.py candidate.plugin")
    sys.exit(check(sys.argv[1]))
