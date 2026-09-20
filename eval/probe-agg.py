#!/usr/bin/env python3
"""Rebuild SUMMARY.tsv (one row per run) and AGG.tsv (one row per probe) for a probe batch directory.
Derived files only: reads <out>/<id>/r<k>*/{meta.json,score.json}, never touches run evidence.
It tabulates scorer exits; it draws no conclusion. Usage: python3 eval/probe-agg.py <out-dir>"""
import json, os, re, sys, tempfile


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write(path, rows):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".agg.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join("\t".join(map(str, r)) for r in rows) + "\n")
    os.replace(tmp, path)


def main(out):
    runs = []
    for ident in sorted(os.listdir(out)):
        base = os.path.join(out, ident)
        if not os.path.isdir(base):
            continue
        for run in sorted(os.listdir(base), key=lambda n: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", n)]):
            if re.fullmatch(r"r\d+(\.retry\d+)?", run) and os.path.isdir(os.path.join(base, run)):
                meta, score = load(os.path.join(base, run, "meta.json")), load(os.path.join(base, run, "score.json"))
                exit_code = meta.get("score_exit", "incomplete")   # no meta.json = the run never finished
                if str(meta.get("run_state", "")).startswith("infra"):
                    exit_code = "infra"   # rate limit / credits / execution error: never a verdict
                runs.append({"id": ident, "run": run, "exit": exit_code, "class": meta.get("class") or "-",
                             "route": meta.get("route") or "-", "channel": score.get("channel", "-"),
                             "terminal": score.get("terminal", "-"), "skills": score.get("distinct_skills", "-"),
                             "first_skill": meta.get("first_skill") or "-", "first_agent": meta.get("first_agent") or "-",
                             "seconds": meta.get("seconds", "-"), "cost": meta.get("cost_usd", "-")})
    cols = ["id", "run", "exit", "class", "route", "channel", "terminal", "skills", "first_skill", "first_agent", "seconds", "cost"]
    write(os.path.join(out, "SUMMARY.tsv"),
          [["id", "run", "exit", "class", "route", "channel", "terminal", "distinct_skills", "first_skill",
            "first_agent", "seconds", "cost_usd"]] + [[r[c] for c in cols] for r in runs])
    agg = [["id", "class", "k_pass/N", "n_fail", "n_unscorable_or_incomplete", "channels", "terminals", "mean_distinct_skills",
            "uninformative_0_of_N"]]   # yes = never passed in this arm: a floor, excluded from the claim in advance
    for ident in sorted({r["id"] for r in runs}):
        mine = [r for r in runs if r["id"] == ident]
        scored = [r for r in mine if r["exit"] in (0, 1)]   # N = scored runs only; the rest is listed, never hidden
        count = lambda key: ",".join(f"{v}:{sum(1 for r in scored if r[key] == v)}" for v in sorted({str(r[key]) for r in scored})) or "-"
        nums = [r["skills"] for r in scored if isinstance(r["skills"], int)]
        agg.append([ident, mine[0]["class"], f"{sum(1 for r in scored if r['exit'] == 0)}/{len(scored)}",
                    sum(1 for r in scored if r["exit"] == 1), len(mine) - len(scored), count("channel"), count("terminal"),
                    f"{sum(nums) / len(nums):.2f}" if nums else "-",
                    "yes" if scored and not any(r["exit"] == 0 for r in scored) else "no"])
    write(os.path.join(out, "AGG.tsv"), agg)
    total = sum(r["cost"] for r in runs if isinstance(r["cost"], (int, float)))
    print(f"runs={len(runs)} scored={sum(1 for r in runs if r['exit'] in (0, 1))} cost_usd={total:.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
