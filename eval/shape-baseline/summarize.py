#!/usr/bin/env python3
"""Aggregate every run under a results root into SUMMARY.tsv and SPAWNS.tsv (raw numbers, no judgement added).

    python3 eval/shape-baseline/summarize.py eval/shape-baseline/results/<arm>-<batch>
"""
import glob, json, os, sys

root = sys.argv[1].rstrip("/")
runs = sorted(glob.glob(os.path.join(root, "S*", "r*", "metrics.json")))
head = ["scenario", "rep", "arm", "distribution", "verdict", "quality_auto", "boundary_auto", "human_read_open", "result",
        "cost_usd", "wall_s", "spawns", "spawn_types", "models_served", "tok_input", "tok_cache_read", "tok_cache_creation",
        "tok_output", "tok_total", "main_usd", "spawn_host_static_usd", "spawn_plugin_static_usd", "spawn_work_usd",
        "main_host_static_usd", "main_plugin_static_usd", "main_work_usd", "blocked_tool_attempts", "cli", "plugin_version", "arm_only"]
shead = ["scenario", "rep", "thread", "agent_type", "roles", "model", "shape", "api_calls", "ctx_first", "ctx_last", "host_static_tok",
         "plugin_static_tok", "delegation_tok_est", "tok_input", "tok_cache_read", "tok_cache_creation", "tok_output", "cost_usd",
         "usd_host_static", "usd_plugin_static", "usd_plugin_load", "usd_delegation", "usd_work_input", "usd_output", "seconds",
         "plugin_load_files", "body_matches_arm"]
rows, srows = [], []


def secs(a, b):
    from datetime import datetime
    try:
        f = "%Y-%m-%dT%H:%M:%S.%fZ"
        return round((datetime.strptime(b, f) - datetime.strptime(a, f)).total_seconds(), 1)
    except (TypeError, ValueError):
        return ""


for mp in runs:
    d = os.path.dirname(mp)
    m = json.load(open(mp, encoding="utf-8"))
    meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    try:
        s = json.load(open(os.path.join(d, "score.json"), encoding="utf-8"))
    except OSError:
        s = {}
    t, dr, tk = m["totals"], m["cost_drivers_usd"], m["totals"]["tokens"]
    rows.append([meta["scenario"], meta["rep"], meta["arm"], meta["distribution"], s.get("verdict"), s.get("quality_auto_ok"),
                 s.get("boundary_auto_ok"), len(s.get("human_read", [])), t["result_subtype"], round(t["cost_usd_host"] or 0, 4),
                 t["wall_seconds"], t["spawn_count"], json.dumps(t["spawn_types"]), ",".join(m["served"]["models"]),
                 tk.get("input", 0), tk.get("cache_read", 0), tk.get("cache_creation", 0), tk.get("output", 0), t["tokens_all"],
                 dr["main_session_usd"], dr["spawn_host_static_usd"], dr["spawn_plugin_static_usd"], dr["spawn_work_usd"],
                 dr["main_host_static_usd"], dr["main_plugin_static_usd"], dr["main_work_usd"],
                 json.dumps(s.get("blocked_tool_attempts", []), ensure_ascii=False), m["served"]["cli_version"],
                 meta["plugin_manifest_version"], m["served"]["plugin_is_arm_only"]])
    for th in m["threads"]:
        c, k = th["cost_by_class_usd"], th["tokens"]
        srows.append([meta["scenario"], meta["rep"], th["thread"], th["agent_type"], "+".join(th["roles"]), ",".join(th["models"]),
                      th.get("request_shape", ""), th["api_calls"], th["ctx_first_call"], th["ctx_last_call"],
                      th["static_tokens"]["host_static"], th["static_tokens"]["plugin_static"], th["static_tokens"]["delegation"],
                      k["input"], k["cache_read"], k["cache_creation"], k["output"], th["cost_usd"], c["host_static"],
                      c["plugin_static"], c["plugin_load"], c["delegation"], c["work_input"], c["output"],
                      secs(th["t_start"], th["t_end"]), len(th["plugin_load_calls"]), th.get("agent_body_matches_arm_file", "")])
for name, h, rr in (("SUMMARY.tsv", head, rows), ("SPAWNS.tsv", shead, srows)):
    with open(os.path.join(root, name), "w", encoding="utf-8") as fh:
        fh.write("\t".join(h) + "\n")
        for r in rr:
            fh.write("\t".join(str(x) for x in r) + "\n")
print(f"{len(rows)} runs, {len(srows)} threads -> {root}/SUMMARY.tsv, SPAWNS.tsv")
