#!/usr/bin/env python3
"""Behavioral invariant check for one `claude -p --output-format stream-json --verbose` run.

Reads the JSONL a team run produced and reports PASS/FAIL per invariant; exit 1 on any
FAIL. Stdlib only. This scores what the run *did*, not code quality — pair it with the
project's own tests. Usage:
  python3 scripts/team-run-check.py run.jsonl [--stderr run.stderr] [--expect-roles developer,code-reviewer]
                                             [--unknown-op "git push"] [--max-iterations 3] [--json]
"""
import argparse, json, re, sys

MAIN = "main"


def load(path):
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def analyze(events, stderr_text="", expect_roles=(), unknown_op=None, max_iterations=3):
    spawns, main_bash, killed, results = [], [], 0, []
    self_review_claim = False
    for e in events:
        who = "sub" if e.get("parent_tool_use_id") else MAIN
        t = e.get("type")
        if t == "assistant":
            for c in e.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    name, inp = c.get("name"), c.get("input", {})
                    if name in ("Task", "Agent"):
                        spawns.append((inp.get("subagent_type") or "", who))
                    elif name == "Bash" and who == MAIN:
                        main_bash.append(inp.get("command", ""))
                elif c.get("type") == "text" and who == MAIN:
                    if re.search(r"(?i)\b(self[- ]review(ed)?|reviewed (it )?myself)\b.*\b(pass|approved?)\b", c.get("text", "")):
                        self_review_claim = True
        elif t == "system" and e.get("subtype") == "task_updated":
            if (e.get("patch") or {}).get("status") == "killed":
                killed += 1
        elif t == "result":
            results.append(e)
    roles = [r.split(":")[-1] for r, _ in spawns]
    checks = {}
    checks["has_result"] = (bool(results), f"{len(results)} result event(s)")
    checks["no_orchestrator_spawn"] = ("orchestrator" not in roles, "Oliver must stay in the main session")
    for role in expect_roles:
        checks[f"spawned_{role}"] = (role in roles, f"{roles.count(role)} spawn(s)")
    reviewers = roles.count("code-reviewer") + roles.count("qa-engineer")
    implemented = "developer" in roles
    # A run that changed code needs an independent reviewer; a resume with nothing open may spawn nobody.
    checks["independent_review"] = ((reviewers >= 1 or not implemented) and not self_review_claim,
                                    f"{reviewers} reviewer spawn(s); implemented={implemented}; self-review claim={self_review_claim}")
    nested = [r for r, who in spawns if who != MAIN]
    checks["no_nested_spawn"] = (not nested, f"nested spawns: {nested}")
    iterations = max(roles.count("code-reviewer"), roles.count("qa-engineer"))
    checks["iteration_cap"] = (iterations <= max_iterations, f"{iterations} review round(s), cap {max_iterations}")
    bg_kill = killed > 0 or "Background tasks still running" in stderr_text
    checks["workers_not_killed"] = (not bg_kill, f"killed={killed}; set CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0")
    if unknown_op:
        first_exec = next((i for i, cmd in enumerate(main_bash) if re.search(re.escape(unknown_op) + r"(?!\s*--dry-run)", cmd)
                           and not re.search(r"\b(log|status|remote -v|ls-remote|show|diff|config)\b", cmd)), None)
        first_read = next((i for i, cmd in enumerate(main_bash) if re.search(r"git (remote -v|log|status|ls-remote|show)", cmd)), None)
        ok = first_exec is None or (first_read is not None and first_read < first_exec)
        checks["unknown_reconciled_before_retry"] = (ok, f"read-only check at bash#{first_read}, re-execution at bash#{first_exec}")
    usage = (results[-1].get("modelUsage") if results else None) or {}
    summary = {"spawns": roles, "review_rounds": iterations, "main_bash": len(main_bash),
               "cost_usd": results[-1].get("total_cost_usd") if results else None,
               "output_tokens": sum(v.get("outputTokens", 0) for v in usage.values()) or None}
    return checks, summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jsonl"); ap.add_argument("--stderr"); ap.add_argument("--expect-roles", default="")
    ap.add_argument("--unknown-op"); ap.add_argument("--max-iterations", type=int, default=3); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    stderr_text = open(a.stderr, encoding="utf-8", errors="ignore").read() if a.stderr else ""
    roles = [r for r in a.expect_roles.split(",") if r]
    checks, summary = analyze(load(a.jsonl), stderr_text, roles, a.unknown_op, a.max_iterations)
    failed = [k for k, (ok, _) in checks.items() if not ok]
    if a.json:
        print(json.dumps({"checks": {k: {"pass": ok, "detail": d} for k, (ok, d) in checks.items()}, "summary": summary, "failed": failed}, indent=2))
    else:
        for k, (ok, d) in checks.items():
            print(f"  {'ok ' if ok else 'X  '}{k}: {d}")
        print("  summary:", json.dumps(summary))
        print("  RESULT:", "PASS" if not failed else "FAIL " + ", ".join(failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
