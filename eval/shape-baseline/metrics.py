#!/usr/bin/env python3
"""Usage, cost and static-vs-work attribution for one run of protocol shape-baseline-v1.

    python3 eval/shape-baseline/metrics.py <run-dir> --controls <controls-dir> --plugin-dir <arm tree> \
        --role-map eval/shape-baseline/role-map.<arm>.json [--prompt <prompt.txt>]

Source of every number: the session transcript (main.jsonl + subagents/agent-*.jsonl, one usage block per API
call, deduplicated by message.id, last record wins) and the final `result` event of run.jsonl. Nothing is taken
from what an agent says about itself.

Attribution model (per API call). The request context of call c is ctx_c = input + cache_read + cache_creation.
It is cut into ordered segments:
    host_static    H   host system prompt + tool definitions + environment, from the no-plugin CONTROL run
    plugin_static  P   ctx_0 - H - D: agent body + preloaded skills + skill/agent listings (+ command body, main)
    delegation     D   the first user message (bytes / BYTES_PER_TOKEN, an estimate)
    then for every earlier call j: its own output re-read, plugin_load (results of Skill and of Read on a path
    inside the plugin directory = the arm's instructions loaded at run time), work (every other tool result)
Positions are priced the way the API bills a prefix cache: the first cache_read tokens at 0.1x, the next
cache_creation tokens at 1.25x (5 min) or 2x (1 h), the rest at 1x; output at 5x. The base rate per model is
solved from the host-reported costUSD, so the classes sum to the host's own cost figure.
Known error sources are listed in protocol.md § Attribution error.
"""
import argparse, collections, fnmatch, glob, hashlib, json, os, re, sys

BYTES_PER_TOKEN = 3.0      # delegation / user-prompt estimate only; see protocol.md
W_READ, W_C5M, W_C1H, W_OUT = 0.1, 1.25, 2.0, 5.0
CLASSES = ("host_static", "plugin_static", "plugin_load", "delegation", "work_input", "output")


def rows(path):
    out = []
    try:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def blen(obj):
    if obj is None:
        return 0
    if isinstance(obj, str):
        return len(obj.encode("utf-8"))
    if isinstance(obj, list):
        return sum(blen(x.get("text") if isinstance(x, dict) and x.get("type") == "text" else
                        (x.get("content") if isinstance(x, dict) and "content" in x else json.dumps(x, ensure_ascii=False)))
                   for x in obj)
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def parse_thread(path, plugin_dir):
    """-> dict(calls=[...], first_user_bytes, system_prompt, tools, attachments, t0, t1)"""
    recs = rows(path)
    calls, by_id = [], {}
    pending = []          # user-side items since the last assistant record: (kind, bytes, tool_use_id)
    first_user_bytes, system_prompt, tools, atts = None, None, None, collections.Counter()
    t0 = t1 = None
    for r in recs:
        ts = r.get("timestamp")
        if ts:
            t0 = t0 or ts
            t1 = ts
        typ = r.get("type")
        if typ == "attachment":
            a = r.get("attachment") or {}
            atts[a.get("type")] += 1
            if a.get("type") == "prompt_snapshot":
                system_prompt = system_prompt or a.get("systemPrompt")
                if a.get("tools") and tools is None:
                    tools = a.get("tools")
            elif a.get("type") == "output_style_instructions":
                atts["__style__"] = 1
                parse_thread.style = a.get("style")
            continue
        msg = r.get("message") or {}
        if typ == "user":
            content = msg.get("content")
            if first_user_bytes is None and not calls:
                first_user_bytes = blen(content)
                continue
            if isinstance(content, str):
                pending.append(("text", blen(content), None))
            else:
                for c in content or []:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        pending.append(("tool_result", blen(c.get("content")), c.get("tool_use_id")))
                    else:
                        pending.append(("text", blen([c]) if isinstance(c, dict) else blen(c), None))
        elif typ == "assistant" and msg.get("usage") and msg.get("model") != "<synthetic>":
            mid = msg.get("id") or r.get("uuid")
            if mid not in by_id:
                call = {"id": mid, "model": msg.get("model"), "usage": msg["usage"], "tool_uses": [], "incoming": pending,
                        "ts": ts, "text_bytes": 0}
                pending = []
                by_id[mid] = call
                calls.append(call)
            call = by_id[mid]
            call["usage"] = msg["usage"]                      # last wins
            call["ts_end"] = ts
            for c in msg.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    call["tool_uses"].append({"id": c.get("id"), "name": c.get("name"), "input": c.get("input") or {}})
                elif isinstance(c, dict) and c.get("type") == "text":
                    call["text_bytes"] += blen(c.get("text"))
    for c in calls:
        u = c["usage"]
        cc = u.get("cache_creation") or {}
        c["in"] = u.get("input_tokens", 0) or 0
        c["cr"] = u.get("cache_read_input_tokens", 0) or 0
        c["cc"] = u.get("cache_creation_input_tokens", 0) or 0
        c["c1h"] = cc.get("ephemeral_1h_input_tokens", 0) or 0
        c["c5m"] = c["cc"] - c["c1h"]
        c["out"] = u.get("output_tokens", 0) or 0
        c["ctx"] = c["in"] + c["cr"] + c["cc"]
        for t in c["tool_uses"]:
            p = str(t["input"].get("file_path") or "")
            t["plugin_load"] = t["name"] == "Skill" or (t["name"] == "Read" and plugin_dir and os.path.realpath(p).startswith(plugin_dir + os.sep))
    return {"calls": calls, "first_user_bytes": first_user_bytes or 0, "system_prompt": system_prompt, "tools": tools,
            "attachments": dict(atts), "t0": t0, "t1": t1}


def weighted(c):
    return c["in"] + W_READ * c["cr"] + W_C5M * c["c5m"] + W_C1H * c["c1h"] + W_OUT * c["out"]


def allocate(thread, host_static, delegation):
    """-> per-call list of {class: weighted tokens}; also token sizes of the static parts"""
    calls = thread["calls"]
    if not calls:
        return [], {"host_static": 0, "plugin_static": 0, "delegation": 0}, False
    ctx0 = calls[0]["ctx"]
    h = min(host_static, ctx0)
    d = min(delegation, max(0, ctx0 - h))
    p = max(0, ctx0 - h - d)
    segs = [("host_static", h), ("plugin_static", p), ("delegation", d)]
    degraded = False
    out = []
    for i, c in enumerate(calls):
        if i > 0:
            prev = calls[i - 1]
            inc = c["ctx"] - prev["ctx"]
            if inc < 0:                                   # context was compacted: keep proportions, flag it
                degraded = True
                scale = c["ctx"] / max(1, prev["ctx"])
                segs = [(k, v * scale) for k, v in segs]
            else:
                reread = min(prev["out"], inc)
                rest = inc - reread
                load_ids = {t["id"] for t in prev["tool_uses"] if t["plugin_load"]}
                had_skill = any(t["name"] == "Skill" for t in prev["tool_uses"])
                b_load = b_work = 0
                for kind, nbytes, tid in c["incoming"]:
                    if kind == "tool_result" and tid in load_ids:
                        b_load += nbytes
                    elif kind == "text" and had_skill:
                        b_load += nbytes               # skill body arrives as an injected user message
                    else:
                        b_work += nbytes
                tot = b_load + b_work
                load = rest * b_load / tot if tot else 0
                segs = segs + [("work_input", reread), ("plugin_load", load), ("work_input", rest - load)]
        bands = [(c["cr"], W_READ), (c["cc"], (W_C5M * c["c5m"] + W_C1H * c["c1h"]) / c["cc"] if c["cc"] else 0), (c["in"], 1.0)]
        acc = collections.Counter()
        pos, bi, left = 0.0, 0, bands[0][0]
        for k, size in segs:
            remaining = size
            while remaining > 1e-9 and bi < len(bands):
                if left <= 1e-9:
                    bi += 1
                    if bi >= len(bands):
                        break
                    left = bands[bi][0]
                    continue
                take = min(remaining, left)
                acc[k] += take * bands[bi][1]
                remaining -= take
                left -= take
        acc["output"] += c["out"] * W_OUT
        out.append(acc)
    return out, {"host_static": h, "plugin_static": p, "delegation": d}, degraded


def control_host(controls_dir, which):
    """first-call ctx of the null agents keyed (model served, 'bash'|'nobash'), plus main first-call ctx / prompt bytes"""
    d = os.path.join(controls_dir, which, "raw", "transcript")
    res = {}
    for meta_path in glob.glob(os.path.join(d, "subagents", "*.meta.json")):
        meta = json.load(open(meta_path))
        th = parse_thread(meta_path.replace(".meta.json", ".jsonl"), None)
        if th["calls"]:
            names = [t.get("name") if isinstance(t, dict) else t for t in (th["tools"] or [])]
            res.setdefault((th["calls"][0]["model"], "bash" if "Bash" in names else "nobash"), []).append(th["calls"][0]["ctx"])
    main = parse_thread(os.path.join(d, "main.jsonl"), None)
    return {"spawn": {k: min(v) for k, v in res.items()},
            "main_model": main["calls"][0]["model"] if main["calls"] else None,
            "main_ctx0": main["calls"][0]["ctx"] if main["calls"] else 0, "main_prompt_bytes": main["first_user_bytes"]}


def host_static_for(host, model, has_bash):
    """-> (tokens, exact?)  exact = the control measured this model; else the main model's figure is used"""
    key = "bash" if has_bash else "nobash"
    if (model, key) in host["spawn"]:
        return host["spawn"][(model, key)], True
    return host["spawn"].get((host["main_model"], key), 0), False


def role_of(agent_type, prompt, role_map):
    ns = role_map.get("namespace", "")
    bare = agent_type[len(ns):] if agent_type.startswith(ns) else agent_type
    for rule in role_map.get("rules", []):
        if rule["type"] == bare and re.search(rule["prompt_regex"], prompt or ""):
            return rule["roles"]
    if agent_type.startswith(ns) and bare in role_map["types"]:
        return role_map["types"][bare]
    if agent_type in role_map.get("host_builtin_types", []):
        return [role_map.get("host_builtin_role", "host-builtin")]
    return ["unmapped"]


def agent_body(plugin_dir, bare):
    try:
        text = open(os.path.join(plugin_dir, "agents", bare + ".md"), encoding="utf-8").read()
    except OSError:
        return None
    parts = text.split("---", 2)
    return parts[2].strip() if len(parts) == 3 else text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--controls", required=True)
    ap.add_argument("--control-name", default=None, help="with-plugin control (generated|source); default from meta.json")
    ap.add_argument("--plugin-dir", required=True)
    ap.add_argument("--role-map", required=True)
    a = ap.parse_args()
    run = a.run_dir.rstrip("/")
    plugin_dir = os.path.realpath(a.plugin_dir)
    role_map = json.load(open(a.role_map, encoding="utf-8"))
    meta = json.load(open(os.path.join(run, "meta.json"), encoding="utf-8")) if os.path.exists(os.path.join(run, "meta.json")) else {}
    local = json.load(open(os.path.join(run, "raw", "local.json"), encoding="utf-8")) if os.path.exists(os.path.join(run, "raw", "local.json")) else {}
    tdir = os.path.join(run, "raw", "transcript")

    stream = rows(os.path.join(run, "raw", "run.jsonl"))
    init = next((e for e in stream if e.get("type") == "system" and e.get("subtype") == "init"), {})
    results = [e for e in stream if e.get("type") == "result" and not e.get("parent_tool_use_id")]
    result = results[-1] if results else {}
    model_usage = result.get("modelUsage") or {}

    host_np = control_host(a.controls, "noplugin")
    host_wp = control_host(a.controls, a.control_name or meta.get("distribution") or "generated")
    h_main = max(0, host_np["main_ctx0"] - host_np["main_prompt_bytes"] / 4.0)

    parse_thread.style = None
    main_thread = parse_thread(os.path.join(tdir, "main.jsonl"), plugin_dir)
    style = getattr(parse_thread, "style", None)
    spawn_inputs = {}
    for c in main_thread["calls"]:
        for t in c["tool_uses"]:
            if t["name"] in ("Agent", "Task"):
                spawn_inputs[t["id"]] = {"input": t["input"], "ts": c.get("ts")}

    threads = [("main", None, main_thread)]
    for meta_path in sorted(glob.glob(os.path.join(tdir, "subagents", "*.meta.json"))):
        m = json.load(open(meta_path))
        threads.append((os.path.basename(meta_path)[:-len(".meta.json")], m, parse_thread(meta_path.replace(".meta.json", ".jsonl"), plugin_dir)))

    # base rate per model, solved from the host-reported cost
    w_by_model, tok_by_model = collections.Counter(), collections.defaultdict(collections.Counter)
    for _, _, th in threads:
        for c in th["calls"]:
            w_by_model[c["model"]] += weighted(c)
            for k in ("in", "cr", "cc", "c5m", "c1h", "out"):
                tok_by_model[c["model"]][k] += c[k]
    rate, reconcile = {}, {}
    for model, w in w_by_model.items():
        mu = model_usage.get(model) or {}
        rate[model] = (mu.get("costUSD") / w) if mu.get("costUSD") and w else None
        t = tok_by_model[model]
        reconcile[model] = {
            "transcript": {"input": t["in"], "cache_read": t["cr"], "cache_creation": t["cc"], "output": t["out"]},
            "host_modelUsage": {"input": mu.get("inputTokens"), "cache_read": mu.get("cacheReadInputTokens"),
                                "cache_creation": mu.get("cacheCreationInputTokens"), "output": mu.get("outputTokens"),
                                "costUSD": mu.get("costUSD")},
            "base_rate_usd_per_mtok": round(rate[model] * 1e6, 4) if rate[model] else None,
        }
    missing_models = [m for m in model_usage if m not in w_by_model]

    spawns, totals = [], collections.Counter()
    cost_class_total = collections.Counter()
    for name, m, th in threads:
        calls = th["calls"]
        is_main = m is None
        if is_main:
            agent_type, roles, tool_names, prompt = "(main session)", ["router-main"], None, None
            h = h_main
            d = meta.get("prompt_bytes", th["first_user_bytes"]) / BYTES_PER_TOKEN
        else:
            agent_type = m.get("agentType") or "?"
            sp = spawn_inputs.get(m.get("toolUseId"), {})
            prompt = (sp.get("input") or {}).get("prompt") or ""
            roles = role_of(agent_type, prompt, role_map)
            tool_names = [t.get("name") if isinstance(t, dict) else t for t in (th["tools"] or [])]
            has_bash = ("Bash" in tool_names) if tool_names else True
            h, h_exact = host_static_for(host_np, calls[0]["model"] if calls else None, has_bash)
            d = th["first_user_bytes"] / BYTES_PER_TOKEN
        alloc, static, degraded = allocate(th, h, d)
        tok = collections.Counter()
        cost_class = collections.Counter()
        for c, acc in zip(calls, alloc):
            for k in ("in", "cr", "cc", "c5m", "c1h", "out"):
                tok[k] += c[k]
            r = rate.get(c["model"])
            for k, v in acc.items():
                cost_class[k] += v * r if r else 0.0
        bare = agent_type[len(role_map.get("namespace", "")):] if agent_type.startswith(role_map.get("namespace", "")) else agent_type
        body = None if is_main else agent_body(plugin_dir, bare)
        sp0 = (th["system_prompt"] or [""])[0] if th["system_prompt"] else ""
        rec = {
            "thread": name, "agent_type": agent_type, "roles": roles,
            "models": sorted({c["model"] for c in calls}), "api_calls": len(calls),
            "tokens": {"input": tok["in"], "cache_read": tok["cr"], "cache_creation": tok["cc"],
                       "cache_creation_5m": tok["c5m"], "cache_creation_1h": tok["c1h"], "output": tok["out"]},
            "ctx_first_call": calls[0]["ctx"] if calls else 0, "ctx_last_call": calls[-1]["ctx"] if calls else 0,
            "static_tokens": {k: round(v) for k, v in static.items()},
            "first_user_bytes": th["first_user_bytes"],
            "cost_usd": round(sum(cost_class.values()), 6),
            "cost_by_class_usd": {k: round(cost_class.get(k, 0.0), 6) for k in CLASSES},
            "tool_calls": dict(collections.Counter(t["name"] for c in calls for t in c["tool_uses"])),
            "plugin_load_calls": [t["input"].get("skill") or os.path.relpath(os.path.realpath(str(t["input"].get("file_path"))), plugin_dir)
                                  for c in calls for t in c["tool_uses"] if t["plugin_load"]],
            "t_start": th["t0"], "t_end": th["t1"], "attribution_degraded": degraded,
        }
        if not is_main:
            rec["tools_served"] = tool_names
            rec["host_static_measured_for_model"] = h_exact
            rec["system_prompt_bytes"] = [len(x.encode("utf-8")) for x in (th["system_prompt"] or [])]
            rec["agent_body_served_sha256"] = hashlib.sha256(sp0.encode("utf-8")).hexdigest()[:16]
            rec["agent_body_matches_arm_file"] = (body is not None and body[:400] in sp0) if body else None
            rec["delegation_bytes"] = len(prompt.encode("utf-8"))
            rec["subagent_type_requested"] = (spawn_inputs.get(m.get("toolUseId"), {}).get("input") or {}).get("subagent_type")
            rec["model_override"] = (spawn_inputs.get(m.get("toolUseId"), {}).get("input") or {}).get("model")
            rec["request_shape"] = m.get("requestShape")
            rec["tool_use_id"] = m.get("toolUseId")
        spawns.append(rec)
        for k, v in rec["tokens"].items():
            totals[k] += v
        for k in CLASSES:
            scope = "main" if is_main else "spawns"
            cost_class_total[f"{scope}.{k}"] += cost_class.get(k, 0.0)

    n_spawns = len(spawns) - 1
    cc = cost_class_total
    drivers = {
        "main_session_usd": round(sum(v for k, v in cc.items() if k.startswith("main.")), 6),
        "spawn_host_static_usd": round(cc["spawns.host_static"], 6),
        "spawn_plugin_static_usd": round(cc["spawns.plugin_static"] + cc["spawns.plugin_load"], 6),
        "spawn_work_usd": round(cc["spawns.delegation"] + cc["spawns.work_input"] + cc["spawns.output"], 6),
        "main_plugin_static_usd": round(cc["main.plugin_static"] + cc["main.plugin_load"], 6),
        "main_host_static_usd": round(cc["main.host_static"], 6),
        "main_work_usd": round(cc["main.delegation"] + cc["main.work_input"] + cc["main.output"], 6),
    }
    plugins = [p for p in init.get("plugins") or [] if p.get("path") != "builtin"]
    out = {
        "run": "%s/r%s" % (meta.get("scenario"), meta.get("rep")), "scenario": meta.get("scenario"), "arm": meta.get("arm"), "distribution": meta.get("distribution"),
        "served": {
            "cli_version": init.get("claude_code_version"), "main_model": init.get("model"),
            "models": sorted(w_by_model), "non_builtin_plugins": plugins,
            "plugin_is_arm_only": len(plugins) == 1 and os.path.realpath(plugins[0].get("path", "")) == plugin_dir,
            "mcp_servers": len(init.get("mcp_servers") or []), "permission_mode": init.get("permissionMode"),
            "output_style_bytes": len(style.encode("utf-8")) if isinstance(style, str) else (len(json.dumps(style)) if style else 0),
        },
        "totals": {
            "tokens": dict(totals), "tokens_all": sum(totals[k] for k in ("input", "cache_read", "cache_creation", "output")),
            "cost_usd_host": result.get("total_cost_usd"), "cost_usd_allocated": round(sum(s["cost_usd"] for s in spawns), 6),
            "wall_seconds": meta.get("seconds"), "duration_ms_last_result": result.get("duration_ms"),
            "duration_api_ms": result.get("duration_api_ms"), "num_turns": result.get("num_turns"),
            "result_subtype": result.get("subtype"), "result_events": len(results),
            "spawn_count": n_spawns, "spawn_types": dict(collections.Counter(s["agent_type"] for s in spawns[1:])),
            "permission_denials": result.get("permission_denials") or [],
        },
        "cost_drivers_usd": drivers,
        "controls": {"host_static_tokens_main": round(h_main),
                     "host_static_tokens_spawn": {f"{k[0]}|{k[1]}": v for k, v in sorted(host_np["spawn"].items(), key=str)},
                     "with_plugin_tokens_spawn": {f"{k[0]}|{k[1]}": v for k, v in sorted(host_wp["spawn"].items(), key=str)}},
        "reconcile": reconcile, "models_in_host_usage_but_not_in_transcripts": missing_models,
        "threads": spawns,
    }
    json.dump(out, open(os.path.join(run, "metrics.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    t = out["totals"]
    print(f"{meta.get('scenario')} r{meta.get('rep')}: cost ${t['cost_usd_host']} (allocated ${t['cost_usd_allocated']}), "
          f"{t['wall_seconds']}s, spawns={n_spawns} {t['spawn_types']}, tokens in={totals['input']} cr={totals['cache_read']} "
          f"cc={totals['cache_creation']} out={totals['output']}")
    print(" drivers:", drivers)
    for s in spawns:
        print(f"  {s['thread'][:22]:22} {s['agent_type']:32} {','.join(s['models']):18} calls={s['api_calls']:3} ctx0={s['ctx_first_call']:6} "
              f"static={s['static_tokens']} ${s['cost_usd']:.4f} {s['cost_by_class_usd']}")


if __name__ == "__main__":
    main()
