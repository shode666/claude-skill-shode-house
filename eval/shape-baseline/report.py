#!/usr/bin/env python3
"""Aggregate one matrix batch into REPORT.md tables (analysis helper, not part of the frozen scorer).

    python3 eval/shape-baseline/report.py eval/shape-baseline/results/<batch>

Uses the latest scorable run of each slot (r<k>, r<k>.retry<n>). Human-read outcomes are taken from
<batch>/HUMAN-READ.tsv (scenario, rep, verdict PASS|FAIL, note) when present; a run with open human-read items and
no row there is reported as "auto-pass, unread".

Tokens: the host's own usage totals (`result.modelUsage`, carried in metrics.json `reconcile[model].host_modelUsage`)
are the authoritative figures. metrics.py (frozen) sums the transcripts; where the two differ the difference is shown
per run and per token kind, and its cost is re-attributed as follows (ATTRIBUTION below):
  - a delta can only be output tokens of API calls whose last transcript record is a mid-stream snapshot
    (`stop_reason` null: the record was written before the final usage arrived); input and cache figures are final
    at the first record of a call;
  - when raw/transcript is present, those calls are located by thread; otherwise the delta is assigned to the spawns
    (flagged "not located");
  - per model the base rate is re-solved over transcript weight + 5 x delta (the same weights as metrics.py), every
    class of that model is rescaled by w / (w + 5 x delta), and the remainder goes to the output (work) class of the
    located thread(s), split equally between them. Each run's total stays the host cost.
"""
import collections, csv, glob, json, os, statistics, sys

TOK = ("input", "cache_read", "cache_creation", "output")
W_READ, W_C5M, W_C1H, W_OUT = 0.1, 1.25, 2.0, 5.0      # must equal metrics.py (frozen); checked in reconcile_run
ATTRIBUTION = ("host modelUsage is authoritative; transcript-vs-host delta re-attributed to the output (work) class "
               "of the thread whose last transcript record of a call is a mid-stream snapshot, base rate re-solved per model")


def truncated_calls(run_dir):
    """-> {thread name: [partial output_tokens, ...]} for calls whose last transcript record has stop_reason null;
    None when the raw transcript is not available."""
    tdir = os.path.join(run_dir, "raw", "transcript")
    if not os.path.isdir(tdir):
        return None
    found = {}
    for f in [os.path.join(tdir, "main.jsonl")] + sorted(glob.glob(os.path.join(tdir, "subagents", "*.jsonl"))):
        if not os.path.exists(f):
            continue
        last = {}
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            msg = r.get("message") or {}
            if r.get("type") == "assistant" and msg.get("usage") and msg.get("model") != "<synthetic>":
                last[msg.get("id") or r.get("uuid")] = msg
        name = "main" if f.endswith("main.jsonl") else os.path.basename(f)[:-len(".jsonl")]
        part = [msg["usage"].get("output_tokens", 0) for msg in last.values() if msg.get("stop_reason") is None]
        if part:
            found[name] = part
    return found


def reconcile_run(m, run_dir):
    """host tokens, transcript tokens, per-model delta, reconciled cost drivers and thread costs for one run"""
    host, tr, delta = collections.Counter(), collections.Counter(), {}
    for model, rc in m["reconcile"].items():
        for k in TOK:
            host[k] += rc["host_modelUsage"].get(k) or 0
            tr[k] += rc["transcript"].get(k) or 0
        d = {k: (rc["host_modelUsage"].get(k) or 0) - (rc["transcript"].get(k) or 0) for k in TOK}
        if any(d.values()):
            delta[model] = d
    drivers = dict(m["cost_drivers_usd"])
    th_cost = {th["thread"]: th["cost_usd"] for th in m["threads"]}
    rec = {"host": host, "transcript": tr, "delta": delta, "drivers": drivers, "thread_cost": th_cost, "located": {}, "moved": {}}
    if not delta:
        return rec
    trunc = truncated_calls(run_dir)
    cls = collections.Counter()           # reconciled cost per (scope, class)
    for th in m["threads"]:
        scope = "main" if th["thread"] == "main" else "spawns"
        for k, v in th["cost_by_class_usd"].items():
            cls[(scope, k)] += v
    for model, d in delta.items():
        if any(d[k] for k in TOK if k != "output"):
            sys.exit(f"{m['run']}: {model} differs on input/cache tokens; the attribution method does not cover that")
        ths = [th for th in m["threads"] if th["models"] == [model]]
        w = sum(t["tokens"]["input"] + W_READ * t["tokens"]["cache_read"] + W_C5M * t["tokens"]["cache_creation_5m"]
                + W_C1H * t["tokens"]["cache_creation_1h"] + W_OUT * t["tokens"]["output"] for t in ths)
        cost = m["reconcile"][model]["host_modelUsage"]["costUSD"]
        rate = m["reconcile"][model]["base_rate_usd_per_mtok"]
        if abs(cost / w * 1e6 - rate) > 1e-3:
            sys.exit(f"{m['run']}: {model} weights do not reproduce metrics.py's base rate ({cost / w * 1e6:.4f} vs {rate})")
        s = w / (w + W_OUT * d["output"])
        missing = cost - cost * s
        names = {t["thread"] for t in ths}
        where = [n for n in (trunc or {}) if n in names]
        if trunc is None or not where:
            where = [t["thread"] for t in ths if t["thread"] != "main"] or [t["thread"] for t in ths]
            rec["located"][model] = "not located (no raw transcript); assigned to spawns"
        else:
            atype = {t["thread"]: t["agent_type"].split(":")[-1] for t in ths}
            rec["located"][model] = ", ".join(("main session" if n == "main" else "spawn " + atype[n]) for n in sorted(where))
        share = {n: 1 / len(where) for n in where}
        for t in ths:
            scope = "main" if t["thread"] == "main" else "spawns"
            for k, v in t["cost_by_class_usd"].items():
                cls[(scope, k)] += v * s - v
            add = missing * share.get(t["thread"], 0)
            cls[(scope, "output")] += add
            th_cost[t["thread"]] = t["cost_usd"] * s + add
        rec["moved"][model] = missing
    rec["drivers"] = {
        "main_host_static_usd": cls[("main", "host_static")], "main_plugin_static_usd": cls[("main", "plugin_static")] + cls[("main", "plugin_load")],
        "main_work_usd": cls[("main", "delegation")] + cls[("main", "work_input")] + cls[("main", "output")],
        "spawn_host_static_usd": cls[("spawns", "host_static")], "spawn_plugin_static_usd": cls[("spawns", "plugin_static")] + cls[("spawns", "plugin_load")],
        "spawn_work_usd": cls[("spawns", "delegation")] + cls[("spawns", "work_input")] + cls[("spawns", "output")],
    }
    rec["drivers"]["main_session_usd"] = rec["drivers"]["main_host_static_usd"] + rec["drivers"]["main_plugin_static_usd"] + rec["drivers"]["main_work_usd"]
    return rec

root = sys.argv[1].rstrip("/")
human = {}
hp = os.path.join(root, "HUMAN-READ.tsv")
if os.path.exists(hp):
    for r in csv.DictReader(open(hp, encoding="utf-8"), delimiter="\t"):
        human[(r["scenario"], str(r["rep"]))] = (r["verdict"], r.get("note", ""))

runs, invalid = [], []
for mp in sorted(glob.glob(os.path.join(root, "S*", "r*", "meta.json"))):
    d = os.path.dirname(mp)
    meta = json.load(open(mp, encoding="utf-8"))
    try:
        s = json.load(open(os.path.join(d, "score.json"), encoding="utf-8"))
        m = json.load(open(os.path.join(d, "metrics.json"), encoding="utf-8"))
    except (OSError, ValueError):
        invalid.append((meta["scenario"], meta["rep"], "no score/metrics"))
        continue
    if s["verdict"] == "UNSCORABLE":
        invalid.append((meta["scenario"], meta["rep"], "; ".join(s["invalid"])))
        continue
    m["_rec"] = reconcile_run(m, d)
    runs.append((meta, s, m))


def med(xs, nd=3):
    xs = [x for x in xs if x is not None]
    if not xs:
        return "-"
    f = (lambda v: f"{v:,.0f}") if nd == 0 else (lambda v: f"{v:.{nd}f}")
    return f"{f(statistics.median(xs))} ({f(min(xs))}–{f(max(xs))})"


out = []
P = out.append
P("| Scenario | Valid runs | Quality pass | Boundary pass | Completed | Cost USD median (range) | Wall s | Spawns | Agent types (count over runs) | Models served |")
P("|---|---:|---:|---:|---:|---|---|---|---|---|")
tot = collections.Counter()
by_s = collections.defaultdict(list)
for r in runs:
    by_s[r[0]["scenario"]].append(r)
completed_all, cost_all = 0, 0.0
rows_tok, rows_attr, fails, attempts, recon_rows = [], [], [], [], []
agg = collections.Counter()
for sid in sorted(by_s):
    rs = by_s[sid]
    q = b = c = 0
    types, models = collections.Counter(), set()
    for meta, s, m in rs:
        hv = human.get((sid, str(meta["rep"])))
        q_ok, b_ok = s["quality_auto_ok"], s["boundary_auto_ok"]
        if hv and hv[0] == "FAIL":
            q_ok = False
        q += q_ok
        b += b_ok
        done = q_ok and b_ok and (not s["human_read"] or (hv and hv[0] == "PASS"))
        c += bool(done)
        for t, n in m["totals"]["spawn_types"].items():
            types[t.split(":")[-1]] += n
        for th in m["threads"]:
            models.update(th["models"])
        for ck in s["checks"]:
            if not ck["ok"]:
                fails.append((sid, meta["rep"], ck["group"], ck["check"], ck["detail"][:200]))
        if hv and hv[0] == "FAIL":
            fails.append((sid, meta["rep"], "quality (human read)", hv[1], ""))
        for a in s.get("blocked_tool_attempts", []):
            attempts.append((sid, meta["rep"], a[0], "+".join(a[1]), ",".join(a[2])))
        rec = m["_rec"]
        for k, v in rec["drivers"].items():
            agg[k] += v
        for k, v in m["cost_drivers_usd"].items():
            agg["alloc|" + k] += v
        agg["cost"] += m["totals"]["cost_usd_host"] or 0
        for k in TOK:
            agg["tok_" + k] += rec["host"][k]
            agg["tr_" + k] += rec["transcript"][k]
        if rec["delta"]:
            recon_rows.append((sid, meta["rep"], rec))
        agg["spawns"] += m["totals"]["spawn_count"]
        agg["wall"] += m["totals"]["wall_seconds"] or 0
        for th in m["threads"][1:]:
            tc = rec["thread_cost"][th["thread"]]
            agg["spawn_cost"] += tc
            for mm in th["models"]:
                agg["spawn_cost|" + mm] += tc / len(th["models"])
                agg["spawn_n|" + mm] += 1 / len(th["models"])
    cost = [m["totals"]["cost_usd_host"] for _, _, m in rs]
    completed_all += c
    cost_all += sum(cost)
    P(f"| {sid} | {len(rs)} | {q}/{len(rs)} | {b}/{len(rs)} | {c}/{len(rs)} | {med(cost)} | {med([m['totals']['wall_seconds'] for _, _, m in rs], 0)} | "
      f"{med([m['totals']['spawn_count'] for _, _, m in rs], 0)} | {', '.join(f'{k} {v}' for k, v in sorted(types.items())) or '—'} | {', '.join(sorted(x.replace('claude-', '') for x in models))} |")
    tk = lambda key: med([m["_rec"]["host"][key] for _, _, m in rs], 0)
    dout = [(r[0]["rep"], r[2]["_rec"]["host"]["output"] - r[2]["_rec"]["transcript"]["output"]) for r in rs]
    dtxt = ", ".join(f"r{k} +{v:,}" for k, v in dout if v) or "0"
    rows_tok.append(f"| {sid} | {tk('input')} | {tk('cache_read')} | {tk('cache_creation')} | {tk('output')} | {med([sum(m['_rec']['host'].values()) for _, _, m in rs], 0)} | {dtxt} |")
    dk = lambda key: med([m["_rec"]["drivers"][key] for _, _, m in rs])
    rows_attr.append(f"| {sid} | {dk('main_host_static_usd')} | {dk('main_plugin_static_usd')} | {dk('main_work_usd')} | {dk('spawn_host_static_usd')} | {dk('spawn_plugin_static_usd')} | {dk('spawn_work_usd')} | "
                     f"{sum(m['totals']['cost_usd_host'] for _, _, m in rs):.3f} | {c} | {(sum(m['totals']['cost_usd_host'] for _, _, m in rs) / c):.3f} |" if c else
                     f"| {sid} | {dk('main_host_static_usd')} | {dk('main_plugin_static_usd')} | {dk('main_work_usd')} | {dk('spawn_host_static_usd')} | {dk('spawn_plugin_static_usd')} | {dk('spawn_work_usd')} | "
                     f"{sum(m['totals']['cost_usd_host'] for _, _, m in rs):.3f} | 0 | n/a (none completed) |")
P("")
P("Tokens per run, median (range), host usage totals (`result.modelUsage`); last column: output tokens host minus transcript sum, runs where it is not 0:")
P("")
P("| Scenario | Input | Cache read | Cache creation | Output | Total | Output Δ host − transcript |")
P("|---|---|---|---|---|---|---|")
out += rows_tok
P("")
P("Cost by class per run, USD median (range), and cost per completed task:")
P("")
P("| Scenario | Main: host static | Main: plugin static | Main: work | Spawns: host static | Spawns: plugin static + load | Spawns: work | Σ cost all valid runs | Completed | Cost per completed task |")
P("|---|---|---|---|---|---|---|---:|---:|---:|")
out += rows_attr
P("")
c = agg["cost"]
P(f"Batch totals: {len(runs)} valid runs, {agg['spawns']} spawns, ${c:.3f}, {agg['wall']:.0f} s run time; tokens (host usage) input {agg['tok_input']:,} / cache read {agg['tok_cache_read']:,} / "
  f"cache creation {agg['tok_cache_creation']:,} / output {agg['tok_output']:,}. Completed {completed_all}/{len(runs)}; overall cost per completed task "
  + (f"${cost_all / completed_all:.3f}." if completed_all else "n/a."))
P("")
P("Token reconciliation, transcript sum (metrics.py) vs host usage, Δ = host − transcript:")
P("")
P("| Token kind | Transcript sum | Host usage | Δ |")
P("|---|---:|---:|---:|")
for k, label in zip(TOK, ("Input", "Cache read", "Cache creation", "Output")):
    P(f"| {label} | {agg['tr_' + k]:,} | {agg['tok_' + k]:,} | {agg['tok_' + k] - agg['tr_' + k]:+,} |")
P("")
P(f"Runs with a non-zero Δ: {len(recon_rows)} of {len(runs)}" + (":" if recon_rows else "."))
if recon_rows:
    P("")
    P("| Scenario | Rep | Model | Δ input | Δ cache read | Δ cache creation | Δ output | Calls with a mid-stream last record (thread) | Cost moved into their work class, USD |")
    P("|---|---|---|---:|---:|---:|---:|---|---:|")
    for sid, rep, rec in recon_rows:
        for model, d in sorted(rec["delta"].items()):
            P(f"| {sid} | r{rep} | {model.replace('claude-', '')} | {d['input']:+,} | {d['cache_read']:+,} | {d['cache_creation']:+,} | {d['output']:+,} | {rec['located'][model]} | {rec['moved'][model]:.4f} |")
P("")
P("Attribution method: " + ATTRIBUTION + ". Run totals (host cost) are unchanged; only the split between classes moves.")
P("")
P("| Class | USD (reconciled) | Share | USD as allocated by metrics.py (transcript tokens) | Δ USD |")
P("|---|---:|---:|---:|---:|")
for k, label in (("main_host_static_usd", "Main session: host static"), ("main_plugin_static_usd", "Main session: plugin static"), ("main_work_usd", "Main session: work"),
                 ("spawn_host_static_usd", "Spawns: host static (per-spawn overhead)"), ("spawn_plugin_static_usd", "Spawns: plugin static + run-time load"), ("spawn_work_usd", "Spawns: work")):
    P(f"| {label} | {agg[k]:.3f} | {100 * agg[k] / c:.1f} % | {agg['alloc|' + k]:.3f} | {agg[k] - agg['alloc|' + k]:+.4f} |")
P("")
P("Spawn cost by model served: " + "; ".join(f"{k.split('|')[1]}: {agg['spawn_n|' + k.split('|')[1]]:.0f} spawns, ${v:.3f}, mean ${v / agg['spawn_n|' + k.split('|')[1]]:.3f}"
                                               for k, v in sorted(agg.items()) if k.startswith("spawn_cost|")))
P("")
P("Failed checks:")
P("")
P("| Scenario | Rep | Group | Check | Detail |")
P("|---|---|---|---|---|")
for f in fails:
    P("| " + " | ".join(str(x).replace("|", "/").replace("\n", " ") for x in f) + " |")
P("")
P("Out-of-list tool attempts refused by the host:")
P("")
P("| Scenario | Rep | Agent type | Role | Tool |")
P("|---|---|---|---|---|")
for a in attempts:
    P("| " + " | ".join(str(x) for x in a) + " |")
P("")
P("Unscorable runs (kept, slot re-run): " + ("; ".join(f"{a} r{b}: {c_}" for a, b, c_ in invalid) or "none"))
open(os.path.join(root, "REPORT.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
