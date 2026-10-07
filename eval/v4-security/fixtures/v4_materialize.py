"""Turn a compact case spec into a run directory in the host's transcript layout.

The layout and record shapes are the ones Claude Code 2.1.286 writes and eval/shape-baseline reads
(raw/transcript/main.jsonl, subagents/agent-<id>.jsonl + .meta.json, raw/local.json, raw/run.jsonl). The
cases are SYNTHETIC: each is written to exercise one rule, not recorded from a live model. The parser is
checked against real recorded transcripts separately (tests: frozen score.py thread() reads these files).

Case spec (JSON):
  {"name", "rule", "kind": "must-fail" | "must-pass",
   "scenario": "S1" (optional), "expect": {...} (optional expectation block),
   "counts": {"<rule>": n, ...}   every counted rule not listed must be 0,
   "expect_ok": {"<expectation>": true|false},  "g10c_verdict": "PASS" | "FAIL" | "NOT-EXERCISED",
   "files": {"<fixture-relative path>": "<content>"},
   "main": [event, ...], "spawns": {"<sid>": {"type", "delegation", "events": [...], "handback"}}}
Events: {"user": t} · {"user_meta": t} · {"text": t} · {"tool": name, "input": {...}, "result": t, "error": b}
        · {"attachment": {...}}  a `type: attachment` record with that attachment body, in the recorded shapes
          (hook_additional_context, hook_success, instructions, file, edited_text_file, queued_command, ...)
        · {"tools": [<tool event>, ...]}  one API call written as one record per tool_use block (SP-1)
        · {"spawn": "<sid>"}  (main only) Agent call; the spawn's events run; then its hand-back
Strings may use {F} (fixture dir), {P} (plugin dir), {H64} (a fixed 64-hex hash) and {HDR} (the router
header line `router: shode-house@4.0.0 task:t-1 phase:2 iter:1`).

Run evidence (V-1 / H-2): by default a valid run is written: raw/run.jsonl with an init record (the arm as the
only plugin, the pinned model) and a top-level `success` result, and meta.json with main_model_requested. A case
can break the evidence on purpose:
  "result": {...} | null     fields merged into the result event; null = no result event
  "init": {...}              fields merged into the init record (e.g. another model, a second plugin)
  "no_run_jsonl": true       raw/run.jsonl is not written
  "no_meta": true            meta.json is not written;  "meta": {...} fields merged into it
  "main_raw": "<text>"       main.jsonl is written with exactly this text (e.g. "" or "not json\n")
  "drop_spawn_meta": [sid]   that spawn's .meta.json is removed;  "drop_spawn_transcript": [sid] its .jsonl
Round 5 (B1, S3-1, S3-3, N-1, F4):
  every arm spawn (`shode-house:<type>`, with a plugin dir) gets the host's `prompt_snapshot` attachment after the
  delegation, its `systemPrompt[0]` holding the arm's agents/<type>.md body, as a served arm spawn records it;
  "spawn_system_prompt": {sid: [..] | null}  that spawn's systemPrompt instead (null: no snapshot record)
  "spawn_raw": {sid: "<text>"}               that spawn's .jsonl is exactly this text
  "spawn_keep_lines": {sid: n}               only the first n lines of that spawn's .jsonl are kept
  "spawn_corrupt_tool_line": {sid: "keep-result" | "drop-result"}  the first tool_use line is truncated (its
                                             tool_result line kept or removed)
  "spawn_meta_raw": {sid: "<text>"}          that spawn's .meta.json is exactly this text
  "spawn_message_not_object": [sid]          round 6 (Chris r3 M-1): the first tool_use record of that spawn
                                             keeps its line but its `message` is a JSON string, not an object
  "orphan_spawns": [sid]     main gets no Agent call / result for that spawn (its files are still written)
  "main_insert_line": "<text>"  a raw line inserted as main.jsonl line 2;  "main_corrupt_agent_call": true
  "no_main_jsonl": true      main.jsonl is not written;  "remove_fixture": true  the fixture dir is removed last
  "no_local_json": true      raw/local.json is not written;  "meta_raw": "<text>" meta.json is exactly this text
  "run_jsonl_extra": "<text>"  raw text appended to raw/run.jsonl
"""
import datetime
import json
import os

H64 = "a" * 63 + "1"
HDR = "router: shode-house@4.0.0 task:t-1 phase:2 iter:1"
EPOCH = datetime.datetime(2026, 10, 4, 0, 0, 0)
MODEL = "claude-sonnet-5-5"

# ADR iter 5 section 5.2 roster (4.0.0), used to write the synthetic arm's agents/*.md tools: lines.
ROSTER = {
    "product-manager": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"],
    "business-analyst": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "Skill"],
    "ux-ui-designer": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"],
    "solution-architect": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"],
    "staff-engineer": ["Read", "Grep", "Glob", "Bash", "WebSearch", "Write", "Edit", "Skill"],
    "security-engineer": ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "WebSearch", "Skill"],
    "developer": ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Skill"],
    "code-reviewer": ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Skill"],
    "qa-engineer": ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Skill"],
    "devops-engineer": ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Skill"],
    "sre-engineer": ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Skill"],
    "fintech-expert": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"],
    "trading-expert": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"],
    "insurance-expert": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"],
    "sap-expert": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"],
    "erp-expert": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "Skill"],
    "booking-expert": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"],
    "ecommerce-expert": ["Read", "Write", "Edit", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"],
}
PLUGIN_FILES = {
    "references/design-intel/scripts/design_run.py": "# stand-in for the plugin runner\n",
    "references/security/trust-classes.md": "plugin copy\n",
    "references/runbooks/uma-phase-3a.md": "plugin copy\n",
    "skills/discipline/shode-house-discipline/SKILL.md": "---\nname: shode-house-discipline\n---\nplugin copy\n",
}


def make_plugin(dest):
    os.makedirs(os.path.join(dest, ".claude-plugin"), exist_ok=True)
    with open(os.path.join(dest, ".claude-plugin", "plugin.json"), "w") as fh:
        json.dump({"name": "shode-house", "version": "4.0.0"}, fh)
    for t, tools in ROSTER.items():
        p = os.path.join(dest, "agents", t + ".md")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write("---\nname: %s\ndescription: x\nmodel: sonnet\ntools: %s\nskills: [\"shode-house:shode-house-discipline\"]\n---\n"
                     "<!-- floor:begin -->\n## Safety floor\n<!-- floor:end -->\n%s body\n" % (t, json.dumps(tools), t))
    for rel, text in PLUGIN_FILES.items():
        p = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)
    return dest


def _sub(obj, ctx):
    if isinstance(obj, str):
        for k, v in ctx.items():
            obj = obj.replace("{%s}" % k, v)
        return obj
    if isinstance(obj, list):
        return [_sub(x, ctx) for x in obj]
    if isinstance(obj, dict):
        return {k: _sub(v, ctx) for k, v in obj.items()}
    return obj


class _Writer:
    def __init__(self, cwd):
        self.n = 0
        self.ids = 0
        self.cwd = cwd

    def ts(self):
        self.n += 1
        return (EPOCH + datetime.timedelta(seconds=self.n)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def nid(self, prefix):
        self.ids += 1
        return "%s_%04d" % (prefix, self.ids)

    def rec(self, typ, message, **extra):
        r = {"type": typ, "message": message, "timestamp": self.ts(), "uuid": self.nid("u"), "cwd": self.cwd}
        r.update(extra)
        return r


def _tool_records(w, ev, model):
    """-> (assistant records, tool_result record) for one tool or a multi-block call."""
    blocks = ev["tools"] if "tools" in ev else [ev]
    mid = w.nid("msg")
    uses, res = [], []
    for b in blocks:
        tid = w.nid("toolu")
        uses.append({"type": "tool_use", "id": tid, "name": b["tool"], "input": b.get("input", {})})
        res.append({"type": "tool_result", "tool_use_id": tid, "content": b.get("result", ""),
                    "is_error": bool(b.get("error"))})
    usage = {"input_tokens": 1, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 3}
    if "tools" in ev:   # SP-1 shape: one record per tool_use block, the last one a partial snapshot
        recs = [w.rec("assistant", {"id": mid, "model": model, "role": "assistant", "content": [u],
                                    "stop_reason": None, "usage": usage}) for u in uses]
    else:
        recs = [w.rec("assistant", {"id": mid, "model": model, "role": "assistant", "content": uses,
                                    "stop_reason": "tool_use", "usage": usage})]
    return recs, w.rec("user", {"role": "user", "content": res}), uses


def _agent_body(plugin_dir, bare):
    try:
        text = open(os.path.join(plugin_dir, "agents", bare + ".md"), encoding="utf-8").read()
    except (OSError, TypeError):
        return None
    parts = text.split("---", 2)
    return parts[2].strip() if len(parts) == 3 else text.strip()


def _thread(w, events, spawns, sub_dir, model, out, opts=None):
    opts = opts or {}
    for ev in events:
        if "user" in ev:
            out.append(w.rec("user", {"role": "user", "content": ev["user"]}))
        elif "attachment" in ev:      # host attachment record (hook output, CLAUDE.md instructions, @-file, queue)
            out.append({"type": "attachment", "attachment": ev["attachment"], "timestamp": w.ts(), "uuid": w.nid("u"),
                        "cwd": w.cwd})
        elif "user_meta" in ev:
            out.append(w.rec("user", {"role": "user", "content": [{"type": "text", "text": ev["user_meta"]}]}, isMeta=True))
        elif "text" in ev:
            out.append(w.rec("assistant", {"id": w.nid("msg"), "model": model, "role": "assistant",
                                           "content": [{"type": "text", "text": ev["text"]}], "stop_reason": "end_turn",
                                           "usage": {"input_tokens": 1, "output_tokens": 1}}))
        elif "spawn" in ev:
            sid = ev["spawn"]
            sp = spawns[sid]
            tid = w.nid("toolu")
            inp = {"subagent_type": sp["type"], "description": sp.get("description", sid), "prompt": sp.get("delegation", "")}
            out.append(w.rec("assistant", {"id": w.nid("msg"), "model": model, "role": "assistant",
                                           "content": [{"type": "tool_use", "id": tid, "name": "Agent", "input": inp}],
                                           "stop_reason": "tool_use", "usage": {"input_tokens": 1, "output_tokens": 1}}))
            orphan = sid in (opts.get("orphan_spawns") or [])
            if orphan:
                out.pop()                               # no Agent call in main for this spawn
            sub = [w.rec("user", {"role": "user", "content": sp.get("delegation", "")}, isSidechain=True)]
            sysp = (opts.get("spawn_system_prompt") or {}).get(sid, "default")
            if sysp == "default":
                body = _agent_body(opts.get("plugin_dir"), sp["type"][len("shode-house:"):]) \
                    if sp["type"].startswith("shode-house:") else None
                sysp = [body + "\n\n# Environment\n(host text)"] if body is not None else None
            if sysp is not None:
                sub.append({"type": "attachment", "attachment": {"type": "prompt_snapshot", "systemPrompt": sysp},
                            "timestamp": w.ts(), "uuid": w.nid("u"), "cwd": w.cwd, "isSidechain": True})
            _thread(w, sp.get("events", []), spawns, sub_dir, model, sub, opts)
            sub.append(w.rec("assistant", {"id": w.nid("msg"), "model": model, "role": "assistant",
                                           "content": [{"type": "text", "text": sp.get("handback", "")}],
                                           "stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 1}}))
            aid = "agent-" + sid
            lines = [json.dumps(r) for r in sub]
            corrupt = (opts.get("spawn_corrupt_tool_line") or {}).get(sid)
            if corrupt:
                k = next(i for i, ln in enumerate(lines) if '"tool_use"' in ln)
                lines[k] = lines[k][:-40]
                if corrupt == "drop-result":
                    del lines[k + 1]
            if sid in (opts.get("spawn_message_not_object") or []):
                k = next(i for i, ln in enumerate(lines) if '"tool_use"' in ln)
                rec = json.loads(lines[k])
                rec["message"] = json.dumps(rec["message"])
                lines[k] = json.dumps(rec)
            if sid in (opts.get("spawn_keep_lines") or {}):
                lines = lines[:opts["spawn_keep_lines"][sid]]
            with open(os.path.join(sub_dir, aid + ".jsonl"), "w") as fh:
                raw = (opts.get("spawn_raw") or {}).get(sid)
                fh.write(raw if raw is not None else "".join(ln + "\n" for ln in lines))
            with open(os.path.join(sub_dir, aid + ".meta.json"), "w") as fh:
                raw = (opts.get("spawn_meta_raw") or {}).get(sid)
                if raw is not None:
                    fh.write(raw)
                else:
                    json.dump({"agentType": sp["type"], "toolUseId": tid, "requestShape": "foreground"}, fh)
            if orphan:
                continue
            out.append(w.rec("user", {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid,
                                                                   "content": [{"type": "text", "text": sp.get("handback", "")}],
                                                                   "is_error": False}]}))
        else:
            recs, res, _ = _tool_records(w, ev, model)
            out.extend(recs)
            out.append(res)


def materialize(case, dest, plugin_dir=None):
    """Write the case under dest/ (run dir dest/run, fixture dest/fixture). Returns (run_dir, fixture_dir)."""
    run_dir, fixture = os.path.join(dest, "run"), os.path.join(dest, "fixture")
    sub_dir = os.path.join(run_dir, "raw", "transcript", "subagents")
    os.makedirs(sub_dir, exist_ok=True)
    os.makedirs(fixture, exist_ok=True)
    ctx = {"F": fixture, "P": plugin_dir or "/nonexistent-plugin", "H64": H64, "HDR": HDR}
    case = _sub(case, ctx)
    for rel, text in (case.get("files") or {}).items():
        p = os.path.join(fixture, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)
    w = _Writer(fixture)
    main = []
    opts = {k: case.get(k) for k in ("orphan_spawns", "spawn_system_prompt", "spawn_raw", "spawn_keep_lines",
                                     "spawn_corrupt_tool_line", "spawn_meta_raw",
                                     "spawn_message_not_object")}
    opts["plugin_dir"] = plugin_dir
    _thread(w, case.get("main", []), case.get("spawns", {}), sub_dir, MODEL, main, opts)
    lines = [json.dumps(r) for r in main]
    if "main_insert_line" in case:
        lines.insert(1, case["main_insert_line"])
    if case.get("main_corrupt_agent_call"):
        k = next(i for i, ln in enumerate(lines) if '"name": "Agent"' in ln)
        lines[k] = lines[k][:-30]
    if not case.get("no_main_jsonl"):
        with open(os.path.join(run_dir, "raw", "transcript", "main.jsonl"), "w") as fh:
            fh.write(case["main_raw"] if "main_raw" in case else "".join(ln + "\n" for ln in lines))
    for sid in case.get("drop_spawn_meta") or []:
        os.remove(os.path.join(sub_dir, "agent-%s.meta.json" % sid))
    for sid in case.get("drop_spawn_transcript") or []:
        os.remove(os.path.join(sub_dir, "agent-%s.jsonl" % sid))
    if not case.get("no_local_json"):
        with open(os.path.join(run_dir, "raw", "local.json"), "w") as fh:
            json.dump({"fixture": fixture, "plugin_dir": plugin_dir}, fh)
    if not case.get("no_run_jsonl"):
        init = dict({"type": "system", "subtype": "init", "model": MODEL,
                     "plugins": [{"name": "shode-house", "path": plugin_dir or ""}]}, **(case.get("init") or {}))
        recs = [init]
        if case.get("result", {}) is not None:
            recs.append(dict({"type": "result", "subtype": "success", "is_error": False,
                              "result": case.get("final", "done")}, **(case.get("result") or {})))
        with open(os.path.join(run_dir, "raw", "run.jsonl"), "w") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in recs) + case.get("run_jsonl_extra", ""))
    if not case.get("no_meta"):
        with open(os.path.join(run_dir, "meta.json"), "w") as fh:
            if "meta_raw" in case:
                fh.write(case["meta_raw"])
            else:
                json.dump(dict({"scenario": case.get("scenario") or "S1", "arm": "4.0.0-C",
                                "main_model_requested": MODEL}, **(case.get("meta") or {})), fh)
    if case.get("remove_fixture"):
        import shutil
        shutil.rmtree(fixture)
    return run_dir, fixture
