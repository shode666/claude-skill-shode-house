#!/usr/bin/env python3
"""Behavioral invariant check for one `claude -p --output-format stream-json --verbose` run.

Reads the JSONL a team run produced and reports PASS/FAIL per invariant; exit 1 on any
FAIL. Stdlib only. This checks trace structure, not artifact quality or acceptance.
Only synchronous, correlated worker returns are currently verified; background
receipts are not completion evidence. UNKNOWN retries require separate operation-
specific qualification and fail closed here. Usage:
  python3 scripts/team-run-check.py run.jsonl [--stderr run.stderr] [--expect-roles developer,code-reviewer]
                                             [--unknown-op "git push"] [--max-iterations 3] [--json]
  python3 scripts/team-run-check.py run.jsonl --scenario E01 --scenarios eval/scenarios/golden.json [--files run.files]
    scores observable behaviour only (Claude stream-json or Codex `exec --json`); exit 0 PASS / 1 FAIL / 2 UNSCORABLE
    (a scenario carrying `not_applicable` is never scored: exit 2, status NOT_APPLICABLE)
"""
import argparse, fnmatch, json, os, re, shlex, sys

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


# ---------------------------------------------------------------------------
# Scenario scoring (--scenario): observable behaviour only, never reasoning steps.
# ---------------------------------------------------------------------------
SKILL_GROUPS = {"workflow", "ops", "ui", "style", "discipline", "in-progress", "deprecated"}
EDIT_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
SEARCH_CMDS = {"rg", "grep", "find", "ls", "cat", "head", "tail", "sed", "fd", "tree"}
NEUTRAL_CMDS = {"pwd", "cd", "echo"}
R0_STOP = r"(?i)authoriz|confirm|ยืนยัน|อนุญาต|xác nhận"   # vi: E10b p12-r3 stopped with "xin xác nhận"
# Thai questions often carry no "?": a clause ending in a question particle (+ polite ending) is a question.
# Question words (อะไร/ไหน/ยังไง/อย่างไร) count only in a clause without ไม่ ("ไม่ต้องทำอะไร" is a statement);
# nothing counts after the word ว่า ("ตรวจแล้วว่าใช้ได้หรือไม่" is indirect; not กว่า/ว่าง) or on a markdown heading line.
THAI_PARTICLES = ("ไหม", "มั้ย", "มั๊ย", "หรือไม่", "หรือเปล่า", "รึเปล่า", "หรือยัง")
_THAI_Q = r"(ไหม|มั้ย|มั๊ย|หรือไม่|หรือเปล่า|รึเปล่า|หรือยัง|อะไร|ไหน|ยังไง|อย่างไร)(?:\s*(?:ครับ|คะ|ค่ะ|คับ|นะ))*[\s*_)\]\"'`.!]*"
THAI_Q_END, THAI_Q_ANY = re.compile(_THAI_Q + r"\Z"), re.compile(_THAI_Q + r"(?:$|\s[—–]\s)", re.M)
VI_CHARS = set("ơưăđạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ")
VI_CHARS |= {c.upper() for c in VI_CHARS}
EXPECTED_FIELDS = {
    "skills", "must_not_load", "must_not_read", "agents", "must_not_dispatch", "max_spawns", "ask_user",
    "first_action", "requires_r0", "forbidden_commands", "required_commands", "files_touched_glob",
    "files_forbidden_glob", "validation_run", "validation_forbidden", "artifacts", "artifacts_forbidden",
    "result_matches", "route_any", "max_skills", "reply_lang"}
READ_CMDS = {"cat", "head", "tail", "less", "more", "sed", "nl", "bat"}   # search (grep/rg/awk) is not a load
# The routable skills whose descriptions compete for a request (workflow/ops/ui minus the entry skills).
# `max_skills` counts only these; routing/discipline/ask/review-checklist/caveman/domain-core loads are reported.
ROUTABLE_SKILLS = {"api-contract", "automate-test", "data-migration", "decompose", "dev-gate", "diagnose", "drain",
                   "incident", "secure", "slo", "ui-test", "web-q"}
PROBE_TERMINALS = {"success", "error_max_turns"}   # anything else is infrastructure (429, credits, crash), not behaviour
PATH_TOKEN = re.compile(r"[\w.~/@+-]*[\w@+-]\.[A-Za-z0-9]+")


class Unscorable(Exception):
    """The trace or scenario cannot be scored (exit 2); never a PASS and never a behavioural FAIL."""


def skill_of(path):
    """skills/<group>/<name>/... or .agents/skills/<name>/... -> <name>; else None."""
    parts = path.replace("\\", "/").split("/")
    if "skills" not in parts[:-1]:
        return None
    rest = parts[parts.index("skills") + 1:]
    if rest and rest[0] in SKILL_GROUPS:
        rest = rest[1:]
    return rest[0] if len(rest) >= 2 else None


def is_codex(events):
    return any(str(e.get("type", "")).startswith(("item.", "thread.", "turn.")) for e in events)


def _codex_spawn(item):
    """UNVERIFIED: no captured Codex trace contains a spawn (only collab `wait`). Assumed
    shape: collab_tool_call whose tool starts with "spawn", role in agent_type/agent/role."""
    if not str(item.get("tool", "")).startswith("spawn"):
        return None
    role = item.get("agent_type") or item.get("agent") or item.get("role") or ""
    return {"subagent_type": role if isinstance(role, str) else ""}


def normalize_codex(events):
    """Codex CLI `codex exec --json` events -> the stream-json shape used above.
    Verified against test/*/*.jsonl (command_execution, file_change, agent_message,
    turn.completed). A trace without turn.completed yields no result -> UNSCORABLE."""
    out, seen, last_text, usage, failed, turns = [], set(), "", None, False, 0

    def use(ident, name, inp):
        out.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": ident, "name": name, "input": inp}]}})

    for e in events:
        t, item = e.get("type"), e.get("item")
        if t in ("item.started", "item.completed") and isinstance(item, dict):
            ident, kind = str(item.get("id")), item.get("type")
            if kind == "agent_message":
                last_text = item.get("text") if isinstance(item.get("text"), str) else ""
                out.append({"type": "assistant", "message": {"content": [{"type": "text", "text": last_text}]}})
            if kind == "agent_message" or ident in seen:
                continue
            seen.add(ident)
            if kind == "command_execution":
                command = item.get("command") if isinstance(item.get("command"), str) else ""
                try:
                    argv = shlex.split(command)
                except ValueError:
                    argv = []
                if len(argv) == 3 and argv[1] in ("-lc", "-c"):
                    command = argv[2]
                use(ident, "Bash", {"command": command})
            elif kind == "file_change":
                for n, change in enumerate(item.get("changes") or []):
                    if isinstance(change, dict) and isinstance(change.get("path"), str):
                        use(f"{ident}.{n}", "Write" if change.get("kind") == "add" else "Edit",
                            {"file_path": change["path"]})
            elif kind == "collab_tool_call":
                inp = _codex_spawn(item)
                if inp is not None:
                    use(ident, "Agent", inp)
        elif t == "turn.completed":
            turns, usage = turns + 1, e.get("usage") if isinstance(e.get("usage"), dict) else None
        elif t in ("turn.failed", "error"):
            failed = True
    if turns or failed:
        tokens = (usage or {}).get("output_tokens")
        out.append({"type": "result", "subtype": "error" if failed else "success", "is_error": failed,
                    "result": last_text, "modelUsage": {"codex": {"outputTokens": tokens}}})
    return out


def _read_paths(command):
    """Paths a shell command actually READS: only segments whose command is a reader
    (cat/head/tail/less/sed without -i/grep/...). `echo see skills/x/SKILL.md` reads nothing."""
    hits = []
    for seg in re.split(r"&&|\|\||[;|\n]", command):
        words = seg.split()
        if words and words[0] in READ_CMDS and not (words[0] == "sed" and any(w.startswith("-i") for w in words[1:])):
            hits += PATH_TOKEN.findall(seg)
    return hits


def observe(events):
    """Derive observable facts only: tool uses and the final result text.
    Routing facts (skills, agents, routes, first_tool, asks) come from the MAIN session only:
    an event carrying parent_tool_use_id is a sub-agent's and goes to sub_skills / sub_agents.
    Commands, reads and writes stay whole-run (a sub-agent's edit is still an edit)."""
    obs = {"skills": [], "reads": [], "agents": [], "asks": 0, "bash": [], "writes": [],
           "first_tool": None, "results": [], "routes": [], "sub_skills": [], "sub_agents": [],
           "mentions": []}

    def load(name, sub=False):
        name = name.split(":")[-1]
        into = obs["sub_skills"] if sub else obs["skills"]
        if name and name not in into:
            into.append(name)
            if not sub:
                obs["routes"].append("skill:" + name)

    for e in events:
        if e.get("type") == "result" and not e.get("parent_tool_use_id"):
            obs["results"].append(e)
        if e.get("type") != "assistant":
            continue
        for c in blocks(e):
            if c.get("type") != "tool_use":
                continue
            name, inp = c.get("name"), c.get("input") or {}
            if not isinstance(inp, dict):
                raise ValueError("tool_use input must be an object")
            paths, sub = [], bool(e.get("parent_tool_use_id"))
            loadable = None   # paths that may count as a skill load (Read tool / shell READ commands only)
            if name == "Skill":
                # verified live 2026-09-20 (CLI 2.1.269): {"skill": "shode-house:<name>", "args": ...};
                # `command` is a tolerated fallback only; it was never observed in a live trace.
                load(str(inp.get("skill") or inp.get("command") or ""), sub)
            elif name == "Read":
                paths = [str(inp.get("file_path") or "")]
            elif name == "Bash":
                command = str(inp.get("command") or "")
                obs["bash"].append(command)
                paths = PATH_TOKEN.findall(command)
                loadable = _read_paths(command)
                obs["mentions"] += [s for s in map(skill_of, paths) if s and s not in map(skill_of, loadable)]
            elif name in ("Task", "Agent"):
                role = str(inp.get("subagent_type") or "").split(":")[-1]
                (obs["sub_agents"] if sub else obs["agents"]).append(role)
                if not sub:
                    obs["routes"].append("agent:" + role)
            elif name == "AskUserQuestion" and not sub:
                obs["asks"] += 1
            elif name in EDIT_TOOLS:
                obs["writes"].append(str(inp.get(EDIT_TOOLS[name]) or ""))
            loads = [s for s in map(skill_of, paths if loadable is None else loadable) if s]
            for s in loads:
                load(s, sub)
            obs["reads"] += [p for p in paths if p]
            if (obs["first_tool"] is None and name != "Skill" and not loads
                    and not e.get("parent_tool_use_id")):
                obs["first_tool"] = (name, inp)
    last = obs["results"][-1] if obs["results"] else {}
    obs["result_text"] = last.get("result") if isinstance(last.get("result"), str) else ""
    return obs


def describe(scenario, obs):
    """Report-only run descriptors (never part of the verdict): how the route was reached and how the run ended."""
    want = _list((scenario.get("expected") or {}).get("route_any") or [])
    matched = [r for r in obs["routes"] if r in want] if want else obs["routes"]
    channel = matched[0].split(":")[0] if matched else "none"
    last = obs["results"][-1] if obs["results"] else {}
    tail = [ln for ln in obs["result_text"].strip().splitlines() if ln.strip()][-12:]
    options = sum(1 for ln in tail if re.match(r"\s*(?:[-*•]\s*)?\**\(?(?:[A-Da-d]|[1-4])[).:]", ln))   # "A) ... / B) ..." choice
    asked = obs["asks"] > 0 or options >= 2 or any(re.search(r"[?？][\s*_)\]\"'`]*$", ln) for ln in tail)
    subtype = last.get("subtype")
    reply, prompt, match = reply_langs(obs)
    terminal = ("max_turns" if subtype == "error_max_turns" else "asked" if asked and subtype == "success"
                else "completed" if subtype == "success" else f"error:{subtype}")
    return {"channel": channel, "terminal": terminal, "routes": obs["routes"],
            "distinct_skills": len([s for s in obs["skills"] if s in ROUTABLE_SKILLS]),
            "other_skills": [s for s in obs["skills"] if s not in ROUTABLE_SKILLS], "sub_agent_routes": obs["sub_skills"] + obs["sub_agents"],
            "path_mentions_not_counted": obs["mentions"], "reply_lang": reply, "prompt_lang": prompt,
            "reply_lang_match": match}


def thai_q(text, final=False):
    """True when a Thai clause (the last one if `final`) ends in a question particle / question word."""
    for m in (THAI_Q_END if final else THAI_Q_ANY).finditer(text.rstrip() if final else text):
        clause = re.split(r"[.!:—–\n]", text[:m.start()])[-1]
        if re.search(r"(?<!ก)ว่า(?!ง)", clause) or text[:m.start()].rsplit("\n", 1)[-1].lstrip().startswith("#"):
            continue
        if m.group(1) in THAI_PARTICLES or "ไม่" not in clause:
            return True
    return False


def strip_code(text):
    """Drop fenced blocks and inline `code` (a `?` in SQL or a diff is not a question, nor the reply's language)."""
    return re.sub(r"`[^`\n]*`", " ", re.sub(r"```.*?(?:```|\Z)", " ", text, flags=re.S))


def lang_of(text):
    """Report-only script heuristic: th | cjk | vi | en | none (English identifiers inside Thai text are allowed)."""
    thai = sum("\u0e00" <= c <= "\u0e7f" for c in text)
    cjk = sum("\u3040" <= c <= "\u30ff" or "\u3400" <= c <= "\u9fff" or "\uac00" <= c <= "\ud7af" for c in text)
    latin = sum(c.isalpha() and (c < "\u0250" or "\u1e00" <= c <= "\u1eff") for c in text)
    vi, total = sum(c in VI_CHARS for c in text), thai + cjk + latin
    if not total:
        return "none"
    if thai >= 0.2 * total:
        return "th"
    if cjk >= 0.2 * total:
        return "cjk"
    return "vi" if vi >= 3 and vi >= 0.02 * latin else "en"


def reply_langs(obs):
    reply, prompt = lang_of(strip_code(obs["result_text"])), lang_of(strip_code(obs.get("prompt_text") or ""))
    return reply, prompt, (None if "none" in (reply, prompt) else reply == prompt)


def _glob_hit(path, globs):
    """gitignore-like: a path hits when it matches a glob and no later/earlier `!glob`."""
    path = path.replace("\\", "/")
    def match(g):
        return fnmatch.fnmatchcase(path, g) or fnmatch.fnmatchcase(path, "*/" + g)
    return (any(match(g) for g in globs if not g.startswith("!"))
            and not any(match(g[1:]) for g in globs if g.startswith("!")))


def _list(value):
    return [value] if isinstance(value, str) else list(value)


def _found(pattern, texts):
    return any(re.search(pattern, t, re.I | re.M) for t in texts)


def _is_search(tool):
    if tool is None:
        return False
    name, inp = tool
    if name in ("Grep", "Glob", "Read"):
        return True
    if name != "Bash":
        return False
    words = [seg.split()[0] for seg in re.split(r"&&|\|\||[;|]", str(inp.get("command") or "")) if seg.split()]
    return any(w in SEARCH_CMDS for w in words) and all(w in SEARCH_CMDS | NEUTRAL_CMDS for w in words)


def infra_error(result):
    """A probe legitimately ends `success` or `error_max_turns`. Anything else -- error_during_execution, a rate
    limit, exhausted credits, a budget stop, or `success` flagged is_error -- says nothing about routing."""
    subtype = result.get("subtype")
    if subtype not in PROBE_TERMINALS:
        return f"result subtype={subtype}"
    if subtype == "success" and result.get("is_error"):
        return "result subtype=success with is_error=true"
    return None


def score(scenario, obs, files=()):
    """-> checks {name: (ok, detail)} for one scenario's `expected` block."""
    exp, kind = scenario.get("expected"), scenario.get("kind", "core")
    if not isinstance(exp, dict) or kind not in ("core", "probe"):
        raise Unscorable("scenario needs an `expected` object and kind core|probe")
    unknown = set(exp) - EXPECTED_FIELDS
    if unknown:
        raise Unscorable(f"non-observable/unknown expected field(s): {sorted(unknown)}")
    if not obs["results"]:
        raise Unscorable("no result event: trace incomplete")
    infra = infra_error(obs["results"][-1]) if kind == "probe" else None
    if infra:
        raise Unscorable(f"INFRA_ERROR: {infra} -- not behaviour, never scored; re-run this slot")
    checks = {}
    if kind == "core":   # a probe is cut by --max-turns; its result is legitimately not `success`
        last = obs["results"][-1]
        checks["run_succeeded"] = (last.get("subtype") == "success" and not last.get("is_error", False),
                                   f"result subtype={last.get('subtype')}")
    text, bash, skills, agents = obs["result_text"], obs["bash"], obs["skills"], obs["agents"]
    asked = obs["asks"] > 0
    plain = strip_code(text)   # question detection only; R0_STOP / result_matches still see the whole text
    ends_q = bool(re.search(r"[?？][\s*_)\]\"'`]*$", plain)) or thai_q(plain, final=True)
    q_text = "?" in plain or "？" in plain or thai_q(plain)
    known = list(obs["writes"]) + list(files)
    for field, value in exp.items():
        if field == "skills":
            want = _list(value)
            ok = all(s in skills for s in want)
            if kind == "probe" and want:
                ok = skills[:1] == want[:1]
            detail = f"loaded {skills}"
        elif field == "max_skills":   # shotgun over-triggering: cap on DISTINCT main-session skill loads
            counted = [s for s in skills if s in ROUTABLE_SKILLS]
            other = [s for s in skills if s not in ROUTABLE_SKILLS]
            ok, detail = len(counted) <= value, f"{len(counted)} routable skill(s) {counted}, cap {value}; not counted: {other}"
        elif field == "must_not_load":
            bad = [s for s in skills + obs["sub_skills"] if any(fnmatch.fnmatchcase(s, g) for g in _list(value))]
            ok, detail = not bad, f"forbidden loads: {bad}"
        elif field == "must_not_read":
            bad = [p for p in obs["reads"] if _glob_hit(p, _list(value))]
            ok, detail = not bad, f"forbidden reads: {bad}"
        elif field == "agents":
            want = _list(value)
            ok = all(a in agents for a in want)
            if kind == "probe" and want:
                ok = agents[:1] == want[:1]
            detail = f"spawned {agents}"
        elif field == "route_any":   # routed to the skill OR to an owning agent, anywhere in the run
            want = _list(value)
            if not want or any(not isinstance(w, str) or not re.fullmatch(r"(skill|agent):[\w.-]+", w) for w in want):
                raise Unscorable(f"route_any needs a non-empty list of skill:<name> | agent:<role>, got {value!r}")
            hit = [w for w in want if w.split(":", 1)[1] in (skills if w.startswith("skill:") else agents)]
            ok, detail = bool(hit), f"matched {hit}; loaded {skills}, spawned {agents}"
        elif field == "must_not_dispatch":   # whole-run (Quinn Q6), no ordering
            bad = [a for a in agents + obs["sub_agents"] if any(fnmatch.fnmatchcase(a, g) for g in _list(value))]
            ok, detail = not bad, f"forbidden spawns: {bad}"
        elif field == "max_spawns":
            total = len(agents) + len(obs["sub_agents"])
            ok, detail = total <= value, f"{total} spawn(s), cap {value}"
        elif field == "ask_user":
            if value:
                ok = not obs["writes"] and (asked or q_text)
            else:
                ok = not asked and not ends_q
            detail = f"AskUserQuestion={obs['asks']}, result ends with question={ends_q}, writes={len(obs['writes'])}"
        elif field == "first_action":
            tool = obs["first_tool"]
            if value == "search":
                ok = _is_search(tool)
            elif value == "ask":
                ok = tool is not None and tool[0] == "AskUserQuestion"
            elif str(value).startswith("skill:"):
                ok = skills[:1] == [value[6:]]
            elif str(value).startswith("agent:"):
                ok = agents[:1] == [value[6:]]
            else:
                raise Unscorable(f"first_action {value!r} not in search|ask|skill:<name>|agent:<role>")
            detail = f"first tool={tool[0] if tool else None}, first skill={skills[:1]}, first agent={agents[:1]}"
        elif field == "requires_r0":
            if value:   # the command ban itself is the independent forbidden_commands check
                ok, detail = bool(re.search(R0_STOP, text)), "result must ask for authorization/confirmation"
            else:
                ok, detail = not asked and not ends_q, "must proceed without asking"
        elif field in ("forbidden_commands", "validation_forbidden"):
            bad = [p for p in _list(value) if _found(p, bash)]
            ok, detail = not bad, f"matched forbidden pattern(s): {bad}"
        elif field in ("required_commands", "validation_run"):
            missing = [p for p in _list(value) if not _found(p, bash)]
            ok, detail = not missing, f"no Bash command matched: {missing}"
        elif field == "files_touched_glob":
            globs = _list(value)
            stray = [p for p in known if not _glob_hit(p, globs)]
            unmet = [g for g in globs if not g.startswith("!") and not any(_glob_hit(p, [g]) for p in known)]
            ok, detail = not stray and not unmet, f"outside globs: {stray}; globs never touched: {unmet}"
        elif field in ("files_forbidden_glob", "artifacts_forbidden"):
            bad = [p for p in known if _glob_hit(p, _list(value))]
            ok, detail = not bad, f"forbidden paths: {bad}"
        elif field == "artifacts":
            unmet = [g for g in _list(value) if not any(_glob_hit(p, [g]) for p in known)]
            ok, detail = not unmet, f"missing artifacts: {unmet}"
        elif field == "reply_lang":   # opt-in: the final text is in the prompt's language
            if value != "match":
                raise Unscorable(f"reply_lang supports only 'match', got {value!r}")
            reply, prompt, match = reply_langs(obs)
            if prompt == "none":
                raise Unscorable("reply_lang: no prompt text (prompt.txt beside the trace)")
            ok, detail = bool(match), f"reply={reply}, prompt={prompt}"
        elif field == "result_matches":
            missing = [p for p in _list(value) if not _found(p, [text])]
            ok, detail = not missing, f"final text lacks: {missing}"
        checks[field] = (bool(ok), detail)
    return checks


def find_scenario(path, ident):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise Unscorable(f"cannot read scenarios: {exc}") from exc
    items = data.get("scenarios", []) if isinstance(data, dict) else data
    for s in items if isinstance(items, list) else []:
        if isinstance(s, dict) and s.get("id") == ident:
            return s
    raise Unscorable(f"scenario {ident!r} not found in {path}")


def run_scenario(a):
    """Exit 0 PASS / 1 FAIL / 2 UNSCORABLE."""
    try:
        scenario = find_scenario(a.scenarios, a.scenario)
        if scenario.get("not_applicable"):
            raise Unscorable(f"NOT_APPLICABLE: {scenario['not_applicable']}")
        events = load(a.jsonl)
        if is_codex(events):
            events = normalize_codex(events)
        files = []
        if a.files:   # `git status --porcelain` of the fixture after the run
            with open(a.files, encoding="utf-8") as f:
                files = [line[3:].split(" -> ")[-1].strip().strip('"') for line in f if len(line) > 3]
        obs = observe(events)
        prompt = os.path.join(os.path.dirname(os.path.abspath(a.jsonl)), "prompt.txt")   # written by eval/run-lib.sh
        obs["prompt_text"] = (open(prompt, encoding="utf-8").read() if os.path.isfile(prompt)
                              else str(scenario.get("prompt_text") or ""))
        checks, info = score(scenario, obs, files), describe(scenario, obs)
    except (Unscorable, ValueError, TypeError, AttributeError, OSError, re.error) as exc:
        if a.json:
            status = next((k for k in ("NOT_APPLICABLE", "INFRA_ERROR") if str(exc).startswith(k)), "UNSCORABLE")
            print(json.dumps({"scenario": a.scenario, "status": status, "reason": str(exc)}))
        else:
            print(f"  RESULT: UNSCORABLE {exc}")
        sys.exit(2)
    failed = [k for k, (ok, _) in checks.items() if not ok]
    status = "FAIL" if failed else "PASS"
    if a.json:
        print(json.dumps({"scenario": a.scenario, "kind": scenario.get("kind", "core"), "status": status,
                          "checks": {k: {"pass": ok, "detail": d} for k, (ok, d) in checks.items()},
                          "failed": failed, **info}, indent=2))
    else:
        for k, (ok, d) in checks.items():
            print(f"  {'ok ' if ok else 'X  '}{k}: {d}")
        print(f"  info: channel={info['channel']} terminal={info['terminal']} routes={info['routes']} "
              f"distinct_skills={info['distinct_skills']} uncounted_mentions={info['path_mentions_not_counted']}")
        print(f"  info: reply_lang={info['reply_lang']} prompt_lang={info['prompt_lang']} match={info['reply_lang_match']}")
        print(f"  RESULT: {status}" + (" " + ", ".join(failed) if failed else ""))
    sys.exit(1 if failed else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jsonl"); ap.add_argument("--stderr"); ap.add_argument("--expect-roles", default="")
    ap.add_argument("--unknown-op"); ap.add_argument("--max-iterations", type=int, default=3); ap.add_argument("--json", action="store_true")
    ap.add_argument("--scenario", help="scenario id to score (observable `expected` block); exit 0/1/2")
    ap.add_argument("--scenarios", default="eval/scenarios/golden.json")
    ap.add_argument("--files", help="`git status --porcelain` output of the fixture after the run")
    a = ap.parse_args()
    if a.scenario:
        run_scenario(a)
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
