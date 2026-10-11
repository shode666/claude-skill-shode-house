#!/usr/bin/env python3
"""Offline scorer for the 4.0.1 pre-registered probes (E19 served model, E20 spec-axis seeded violations) and the
ordinary-work negative that replaced the staff-engineer must_not_dispatch. It reads thresholds ONLY from
probes-4.0.1.json (pinned by FREEZE.sha256) and never calls a model.

  python3 check-probes.py E19 run1.jsonl ... run5.jsonl
  python3 check-probes.py E20 run1.jsonl ... run5.jsonl [--spec-agent plan|business-analyst] [--baseline-rate 0.85]
  python3 check-probes.py E01 trace.jsonl            # any core-4.0.1.json scenario with post_checks: no-fable-dispatch

Exit 0 PASS, 1 FAIL, 2 UNSCORABLE (the instrument is missing: no modelUsage, a trace count other than the registered run
count, a run with no closed-form verdict line for some criterion). E20 is a structured text scorer: it reads ONLY the closed-form
lines `AC-n: MET` / `AC-n: VIOLATED` (see verdict_lines()); any other wording is not read, and a run that lacks a closed-form line
for a criterion is UNSCORABLE, left to a human to adjudicate. The verdict lines are taken ONLY from the spec reviewer's own
spawn result (the tool_result of its `plan` spawn); the router's final text can only corroborate them (a different verdict there is a
conflict = UNSCORABLE), never supply a line the reviewer's reply lacks."""
import importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
spec = importlib.util.spec_from_file_location("trc", os.path.join(ROOT, "scripts", "team-run-check.py"))
trc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trc)


class Unscorable(Exception):
    pass


def spawns(events):
    """Main-session Task/Agent spawns in order: (type, requested model or '')."""
    out = []
    for e in events:
        if e.get("type") != "assistant" or e.get("parent_tool_use_id"):
            continue
        for c in trc.blocks(e):
            if c.get("type") == "tool_use" and c.get("name") in ("Task", "Agent"):
                inp = c.get("input") or {}
                out.append((str(inp.get("subagent_type") or "").split(":")[-1], str(inp.get("model") or "")))
    return out


def texts(events):
    """The final result text plus every tool_result text (the spawn's returned artifact or reply), joined."""
    return "\n".join(blocks_of_text(events))


def model_usage(events):
    last = [e for e in events if e.get("type") == "result" and not e.get("parent_tool_use_id")]
    usage = last[-1].get("modelUsage") if last else None
    return list(usage) if isinstance(usage, dict) and usage else None


def load(path):
    try:
        return trc.load(path)
    except (OSError, ValueError) as exc:
        raise Unscorable(f"{path}: {exc}")


def run_e19(cfg, events):
    spawn, text, used = spawns(events), texts(events), model_usage(events)
    if used is None:
        raise Unscorable("no modelUsage on the result event: the served model cannot be checked")
    why = []
    if not any(t == cfg["override_type"] and cfg["override_model"] in m.lower() for t, m in spawn):
        why.append(f"no {cfg['override_type']} spawn requested model {cfg['override_model']} (spawns: {spawn})")
    if any(t in cfg["forbidden_spawn_types"] for t, _ in spawn):
        why.append("a forbidden spawn type ran")
    if not re.search(cfg["requested_regex"], text):
        why.append("the requested model is not recorded")
    served = re.search(cfg["served_regex"], text)
    honoured = False
    if not served:
        why.append("the served model is not recorded")
    else:
        token = re.search(cfg["served_token_regex"], served.group(0))
        family = token.group(1).lower() if token else ""
        honoured = family == cfg["override_model"] and any(family in m.lower() for m in used)
        if not honoured and "BLOCKED" not in text:
            why.append(f"served {family or 'unnamed'} vs requested {cfg['override_model']} (modelUsage {used}) without BLOCKED")
    return not why, why, honoured


def blocks_of_text(events):
    """Every text source separately: each tool_result body (a spawn's returned reply) and the final result text."""
    parts = []
    for e in events:
        if e.get("type") == "result" and not e.get("parent_tool_use_id") and isinstance(e.get("result"), str):
            parts.append(e["result"])
        if e.get("type") == "user":
            for c in trc.blocks(e):
                if c.get("type") == "tool_result":
                    body = c.get("content")
                    if isinstance(body, str):
                        parts.append(body)
                    elif isinstance(body, list):
                        parts += [b.get("text", "") for b in body if isinstance(b, dict) and isinstance(b.get("text"), str)]
    return parts


def spec_replies(events, agent):
    """The bodies of the tool_results that answer a main-session spawn of the spec reviewer type (matched on tool_use_id):
    the reviewer's own reply. A tool_result of any other tool or spawn, a sub-agent's internal results and the router's final
    text are not the reviewer's reply."""
    ids = set()
    for e in events:
        if e.get("type") != "assistant" or e.get("parent_tool_use_id"):
            continue
        for c in trc.blocks(e):
            if c.get("type") == "tool_use" and c.get("name") in ("Task", "Agent") and c.get("id") \
                    and str((c.get("input") or {}).get("subagent_type") or "").split(":")[-1] == agent:
                ids.add(c["id"])
    replies = []
    for e in events:
        if e.get("type") != "user" or e.get("parent_tool_use_id"):
            continue
        for c in trc.blocks(e):
            if c.get("type") == "tool_result" and c.get("tool_use_id") in ids:
                body = c.get("content")
                if isinstance(body, str):
                    replies.append(body)
                elif isinstance(body, list):
                    replies.append("\n".join(b.get("text", "") for b in body if isinstance(b, dict) and isinstance(b.get("text"), str)))
    return replies


def final_texts(events):
    return [e["result"] for e in events if e.get("type") == "result" and not e.get("parent_tool_use_id") and isinstance(e.get("result"), str)]


def closed_form(part, ids, line_re, problems):
    """{id: verdict} of the closed-form lines of one text; a second line for an id inside it is a duplicate (UNSCORABLE)."""
    local = {}
    for line in part.splitlines():
        m = line_re.match(line.strip())
        if not m or m.group(1) not in ids:
            continue
        if m.group(1) in local:
            problems.append(f"{m.group(1)}: duplicate closed-form line in one reply")
        local[m.group(1)] = m.group(2)
    return local


def verdict_lines(replies, finals, ids, cfg):
    """Closed form only: ({AC id: MET|VIOLATED}, [problem, ...]). A line counts when the whole stripped line matches
    cfg["verdict_line_regex"] (`AC-n: MET` or `AC-n: VIOLATED`, upper case, nothing else on the line). Nothing else is read: no
    keyword, no negation, no sentence. The verdicts come ONLY from `replies` (the spec reviewer's own spawn result): an id the
    reviewer's reply lacks is "no closed-form line" (UNSCORABLE) even if the router's final text has it. `finals` (the router's
    final text) can only corroborate: a different verdict there is a conflict (UNSCORABLE). Two lines for one id inside one text
    are a duplicate (UNSCORABLE); the same id with different verdicts in two replies is a conflict (UNSCORABLE). An id outside
    `ids` is ignored."""
    line_re = re.compile(cfg["verdict_line_regex"])
    seen, problems = {}, []
    for part in replies:
        for ident, verdict in closed_form(part, ids, line_re, problems).items():
            if seen.get(ident, verdict) != verdict:
                problems.append(f"{ident}: conflicting verdicts ({seen[ident]} vs {verdict})")
            seen.setdefault(ident, verdict)
    for part in finals:
        for ident, verdict in closed_form(part, ids, line_re, problems).items():
            if ident in seen and seen[ident] != verdict:
                problems.append(f"{ident}: conflicting verdicts (reviewer {seen[ident]} vs router final text {verdict})")
    if not replies:
        problems.append("no spec-reviewer reply (the tool_result of its spawn) to read")
    if not seen:
        problems.append("no closed-form `AC-n: MET|VIOLATED` line at all in the spec reviewer's reply")
    problems += [f"{i}: no closed-form line" for i in ids if i not in seen] if seen else []
    return seen, sorted(set(problems))


def run_e20(cfg, events, agent):
    spawn = spawns(events)
    why = []
    if agent not in [t for t, _ in spawn]:
        why.append(f"no {agent} spawn (spawns: {spawn})")
    if any(t in cfg["forbidden_spawn_types"] for t, _ in spawn):
        why.append("a forbidden spawn type ran")
    ids = list(cfg["seeded_violations"]) + list(cfg["decoys_met"])
    v, problems = verdict_lines(spec_replies(events, agent), final_texts(events), ids, cfg)
    caught = [i for i in cfg["seeded_violations"] if v.get(i) == "VIOLATED"]
    false_pos = [i for i in cfg["decoys_met"] if v.get(i) == "VIOLATED"]
    return not why, why, caught, false_pos, v, problems


def probe(ident, cfg, paths, agent, baseline):
    if len(paths) != cfg["runs"]:
        raise Unscorable(f"{ident}: {len(paths)} traces given, exactly {cfg['runs']} registered (a pass rule over a different N is not the registered rule)")
    runs = [load(p) for p in paths]
    if ident == "E19":
        results = [run_e19(cfg, ev) for ev in runs]
        for p, (ok, why, honoured) in zip(paths, results):
            print(f"{p}: {'PASS' if ok else 'FAIL'} override {'honoured' if honoured else 'NOT honoured'} {'; '.join(why)}")
        n, h = sum(r[0] for r in results), sum(r[2] for r in results)
        print(f"E19: {n} of {len(results)} runs record the dispatch correctly (registered {cfg['min_runs_passing']}); "
              f"{h} of {len(results)} served as requested (registered {cfg['min_runs_honoured']}: an honest BLOCKED on a mismatch "
              "passes the router's behaviour but the host did not honour the override)")
        return n >= cfg["min_runs_passing"] and h >= cfg["min_runs_honoured"]
    results = [run_e20(cfg, ev, agent) for ev in runs]
    seeded, decoys = len(cfg["seeded_violations"]), len(cfg["decoys_met"])
    for p, (ok, why, caught, fp, v, problems) in zip(paths, results):
        print(f"{p}: {'ok' if ok else 'BAD'} caught {sorted(caught)} false-positive {sorted(fp)} {'; '.join(why)}")
        for i in list(cfg["seeded_violations"]) + list(cfg["decoys_met"]):   # the closed-form verdict behind every id, for a human to read
            kind = "seeded" if i in cfg["seeded_violations"] else "decoy"
            print(f"    {i} [{kind}] {v.get(i) or 'no closed-form line'}")
        for pr in problems:
            print(f"    UNSCORABLE run: {pr}")
    if not all(r[0] for r in results):                       # a missing spec spawn or a forbidden one is a failed run whatever the text says
        print("  FAIL all runs spawned the spec reviewer")
        return False
    bad = [(p, r[5]) for p, r in zip(paths, results) if r[5]]
    if bad:
        raise Unscorable("E20: " + "; ".join(f"{p}: {', '.join(pr)}" for p, pr in bad) +
                         " -- the reviewer must emit one `AC-n: MET|VIOLATED` line per criterion; a human adjudicates this run")
    catch = sum(len(r[2]) for r in results) / (len(results) * seeded)
    fpr = sum(len(r[3]) for r in results) / (len(results) * decoys)
    t = cfg["threshold"]
    checks = {f"catch rate {catch:.2f} >= {t['min_catch_rate']}": catch >= t["min_catch_rate"],
              f"false-positive rate {fpr:.2f} <= {t['max_false_positive_rate']}": fpr <= t["max_false_positive_rate"]}
    if baseline is not None:
        checks[f"catch rate {catch:.2f} >= 4.0.0 baseline {baseline:.2f}"] = catch >= baseline
    else:
        print("E20: no --baseline-rate given: only the absolute threshold was applied (state this in the report)")
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'} {name}")
    return all(checks.values())


def ordinary(ident, paths, doc):
    scenario = next((s for s in json.load(open(os.path.join(HERE, "core-4.0.1.json"), encoding="utf-8"))["scenarios"] if s["id"] == ident), None)
    if not scenario or "no-fable-dispatch" not in scenario.get("post_checks", []):
        raise Unscorable(f"{ident}: not a probe and has no no-fable-dispatch post_check")
    if len(paths) != 1:
        raise Unscorable("one trace per scenario run")
    events = load(paths[0])
    bad = [(t, m) for t, m in spawns(events) if "fable" in m.lower()]
    used = model_usage(events)
    if used is None:
        print("no modelUsage: checked on the dispatch requests only")
    bad_used = [m for m in used or [] if "fable" in m.lower()]
    print(f"{ident}: fable requests {bad}, fable served {bad_used}")
    return not bad and not bad_used


def main(argv):
    flags, args = {}, []
    it = iter(argv)
    for a in it:
        if a in ("--spec-agent", "--baseline-rate"):
            flags[a] = next(it, None)
        else:
            args.append(a)
    if len(args) < 2:
        print(__doc__)
        return 2
    ident, paths = args[0], args[1:]
    doc = json.load(open(os.path.join(HERE, "probes-4.0.1.json"), encoding="utf-8"))
    try:
        if ident in doc["probes"]:
            agent = flags.get("--spec-agent") or doc["probes"].get("E20", {}).get("spec_agent", {}).get("4.0.1")
            if agent not in ("plan", "business-analyst"):
                raise Unscorable(f"--spec-agent {agent!r}")
            base = float(flags["--baseline-rate"]) if flags.get("--baseline-rate") else None
            ok = probe(ident, doc["probes"][ident], paths, agent, base)
        else:
            ok = ordinary(ident, paths, doc)
    except Unscorable as exc:
        print(f"UNSCORABLE: {exc}")
        return 2
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
