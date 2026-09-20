#!/usr/bin/env python3
"""Behavioral invariant check for one `claude -p --output-format stream-json --verbose` run.

Reads the JSONL a team run produced and reports PASS/FAIL per invariant; exit 1 on any
FAIL. Stdlib only. This checks trace structure, not artifact quality or acceptance.
Only synchronous, correlated worker returns are currently verified; background
receipts are not completion evidence. UNKNOWN retries require separate operation-
specific qualification and fail closed here. Usage:
  python3 scripts/team-run-check.py run.jsonl [--stderr run.stderr] [--expect-roles developer,code-reviewer]
                                             [--unknown-op "git push"] [--max-iterations 3] [--json]
"""
import argparse, json, re, sys

MAIN = "main"


def blocks(event):
    """Validate only the supported trace shape; unknown evidence cannot pass."""
    message = event.get("message") or {}
    if not isinstance(message, dict):
        raise ValueError("message must be an object")
    content = message.get("content") or []
    if not isinstance(content, list) or any(not isinstance(c, dict) for c in content):
        raise ValueError("message.content must be a list of objects")
    return content


def meaningful(content):
    if isinstance(content, str):
        return bool(content.strip())
    return isinstance(content, list) and any(
        isinstance(c, dict) and c.get("type") == "text" and
        isinstance(c.get("text"), str) and c["text"].strip() for c in content)


def load(path):
    events = []
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON trace") from exc
            if not isinstance(events[-1], dict):
                raise ValueError(f"{path}:{number}: event must be an object")
    return events


def analyze(events, stderr_text="", expect_roles=(), unknown_op=None, max_iterations=3):
    spawns, main_bash, killed, results = [], [], 0, []
    self_review_claim = False
    assignments, returns, malformed_ids = {}, {}, False
    all_calls, all_returns = set(), set()
    result_indices, last_activity = [], -1
    for index, e in enumerate(events):
        if not isinstance(e, dict):
            raise ValueError("event must be an object")
        who = "sub" if e.get("parent_tool_use_id") else MAIN
        t = e.get("type")
        if t in ("assistant", "user"):
            last_activity = index
        if t == "assistant":
            for c in blocks(e):
                if c.get("type") == "tool_use":
                    name, inp = c.get("name"), c.get("input", {})
                    ident = c.get("id")
                    if not isinstance(inp, dict) or not isinstance(ident, str) or not ident:
                        raise ValueError("tool_use requires a string id and object input")
                    if ident in all_calls:
                        malformed_ids = True
                    all_calls.add(ident)
                    if name in ("Task", "Agent"):
                        if not isinstance(inp.get("subagent_type", ""), str):
                            raise ValueError("subagent_type must be a string")
                        spawns.append((inp.get("subagent_type") or "", who))
                        ident = c.get("id")
                        if not ident or ident in assignments:
                            malformed_ids = True
                        else:
                            assignments[ident] = {
                                "role": (inp.get("subagent_type") or "").split(":")[-1],
                                "start": index, "background": bool(inp.get("run_in_background")),
                            }
                    elif name == "Bash" and who == MAIN:
                        main_bash.append(inp.get("command", ""))
                elif c.get("type") == "text" and who == MAIN:
                    if re.search(r"(?i)\b(self[- ]review(ed)?|reviewed (it )?myself)\b.*\b(pass|approved?)\b", c.get("text", "")):
                        self_review_claim = True
        elif t == "user" and who == MAIN:
            for c in blocks(e):
                if c.get("type") != "tool_result":
                    continue
                ident = c.get("tool_use_id")
                if not isinstance(ident, str) or not ident:
                    raise ValueError("tool_result requires a string tool_use_id")
                if ident not in all_calls or ident in all_returns:
                    malformed_ids = True
                all_returns.add(ident)
                if ident in assignments:
                    ident = c["tool_use_id"]
                    if ident in returns:
                        malformed_ids = True
                    returns[ident] = (index, not c.get("is_error", False) and meaningful(c.get("content")))
        elif t == "system" and e.get("subtype") == "task_updated":
            if (e.get("patch") or {}).get("status") == "killed":
                killed += 1
        elif t == "result" and who == MAIN:
            results.append(e)
            result_indices.append(index)
    roles = [r.split(":")[-1] for r, _ in spawns]
    checks = {}
    checks["has_result"] = (bool(results), f"{len(results)} result event(s)")
    checks["run_succeeded"] = (len(results) == 1 and results[0].get("subtype") == "success"
                               and not results[0].get("is_error", False)
                               and result_indices[0] > last_activity,
                               "exactly one top-level success after all conversation activity required")
    completed = {ident for ident, a in assignments.items()
                 if not a["background"] and ident in returns and returns[ident][1]
                 and returns[ident][0] > a["start"]}
    checks["worker_returns_complete"] = (not malformed_ids and len(completed) == len(spawns),
        f"{len(completed)}/{len(spawns)} successful correlated synchronous returns; async receipts unsupported")
    checks["no_orchestrator_spawn"] = ("orchestrator" not in roles, "Oliver must stay in the main session")
    for role in expect_roles:
        checks[f"spawned_{role}"] = (role in roles, f"{roles.count(role)} spawn(s)")
    reviewers = roles.count("code-reviewer") + roles.count("qa-engineer")
    implemented = "developer" in roles
    # A run that changed code needs an independent reviewer; a resume with nothing open may spawn nobody.
    implementations = [ident for ident, a in assignments.items() if a["role"] == "developer"]
    reviewed = all(ident in completed and any(
        rid in completed and r["role"] in ("code-reviewer", "qa-engineer")
        and r["start"] > returns[ident][0]
        for rid, r in assignments.items()) for ident in implementations)
    checks["independent_review"] = ((reviewers >= 1 and reviewed or not implemented) and not self_review_claim,
                                    "completed reviewer must start after implementation returns; artifact acceptance not proven")
    nested = [r for r, who in spawns if who != MAIN]
    checks["no_nested_spawn"] = (not nested, f"nested spawns: {nested}")
    iterations = max(roles.count("code-reviewer"), roles.count("qa-engineer"))
    checks["iteration_cap"] = (iterations <= max_iterations, f"{iterations} review round(s), cap {max_iterations}")
    bg_kill = killed > 0 or "Background tasks still running" in stderr_text
    checks["workers_not_killed"] = (not bg_kill, f"killed={killed}; set CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0")
    if unknown_op:
        # Presence of `git status` proves nothing about a remote operation. Do not
        # erase shell lines containing both a read and a write. This conservative
        # textual detector cannot certify aliases, indirect scripts or tool APIs.
        retry = any(unknown_op in cmd for cmd in main_bash)
        checks["unknown_reconciled_before_retry"] = (not retry,
            "retry requires operation-specific evidence unavailable to this checker" if retry else
            "no matching main-shell retry observed; reconciliation itself NOT VERIFIED")
    usage = results[-1].get("modelUsage") if results else None
    usage = {} if usage is None else usage
    if not isinstance(usage, dict):
        raise ValueError("modelUsage must be an object")
    counts = []
    complete_usage = bool(usage)
    for model in usage.values():
        if model is None:
            complete_usage = False
            continue
        if not isinstance(model, dict):
            raise ValueError("per-model usage must be an object or null")
        count = model.get("outputTokens")
        if count is None:
            complete_usage = False
        elif type(count) is not int or count < 0:
            raise ValueError("outputTokens must be a nonnegative integer or null")
        else:
            counts.append(count)
    summary = {"spawns": roles, "review_rounds": iterations, "main_bash": len(main_bash),
               "cost_usd": results[-1].get("total_cost_usd") if results else None,
               "output_tokens": sum(counts) if complete_usage else None,
               "qualification": "trace structure only; artifact/revision acceptance and indirect effects NOT VERIFIED"}
    return checks, summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jsonl"); ap.add_argument("--stderr"); ap.add_argument("--expect-roles", default="")
    ap.add_argument("--unknown-op"); ap.add_argument("--max-iterations", type=int, default=3); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    stderr_text = open(a.stderr, encoding="utf-8", errors="ignore").read() if a.stderr else ""
    roles = [r for r in a.expect_roles.split(",") if r]
    try:
        checks, summary = analyze(load(a.jsonl), stderr_text, roles, a.unknown_op, a.max_iterations)
    except (ValueError, TypeError, AttributeError, OSError) as exc:
        print(f"Invalid or unsupported trace: {exc}", file=sys.stderr)
        sys.exit(1)
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
