#!/usr/bin/env python3
"""U22 H2 / Chris L5: the committed, redacted evidence that the host serves an arm agent's body as exactly
`systemPrompt[0]`, the premise of score_v4.served_body_problems (whole-body equality).

The recorded 3.17.2 runs (eval/shape-baseline/results/*/S*/r*/raw/transcript/subagents/*.jsonl) are git-ignored and
local only, so a test that reads them skips in CI. This module reduces them to what the premise needs and nothing
else: per arm spawn that carries a prompt snapshot, the result set, the slot (scenario/run), the agent type, the arm
file it must equal, the sha256 and length of `systemPrompt[0]`, and how many elements the snapshot has. No prompt
text, host text, path, session or agent id is kept.

    python3 eval/v4-security/fixtures/h2_host_shape.py [<repo-root>]    # rewrites h2-host-shape.json from the data

CI checks the committed records against the agent files at the 3.17.2 release commit (git show); a local run with
the data present also checks that the records are exactly what the data gives.
"""
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "h2-host-shape.json")
REV = "1bc8174b79ba1e4849a6af2e103cf68654ee91e7"   # the 3.17.2 release commit, in full (a short id can grow ambiguous)
NAMESPACE = "shode-house:"


def _rows(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                out.append(r)
    return out


def derive(root):
    """-> the records for every recorded arm spawn with a prompt snapshot under `root`, in a stable order."""
    base = os.path.join(root, "eval", "shape-baseline", "results")
    records = []
    for f in sorted(glob.glob(os.path.join(base, "*", "*", "*", "raw", "transcript", "subagents", "*.jsonl"))):
        rel = os.path.relpath(f, base).split(os.sep)            # <set>/<scenario>/<run>/raw/transcript/subagents/x
        try:
            with open(f[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
                at = json.load(fh).get("agentType", "")
        except (OSError, ValueError):
            continue
        if not at.startswith(NAMESPACE):
            continue
        sp = next((r["attachment"]["systemPrompt"] for r in _rows(f)
                   if (r.get("attachment") or {}).get("type") == "prompt_snapshot"), None)
        if not sp:
            continue
        arm = "" if rel[0].endswith("source") else "plugins/shode-house/"
        records.append({"set": rel[0], "slot": "%s/%s" % (rel[1], rel[2]), "agent_type": at,
                        "arm_file": "%sagents/%s.md" % (arm, at[len(NAMESPACE):]),
                        "sp0_sha256": hashlib.sha256(sp[0].encode("utf-8")).hexdigest(), "sp0_chars": len(sp[0]),
                        "elements": len(sp)})
    records.sort(key=lambda r: (r["set"], r["slot"], r["agent_type"], r["sp0_sha256"], r["elements"]))
    return records


def load():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv):
    root = argv[0] if argv else os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    records = derive(root)
    if not records:
        print("no recorded arm spawns with a prompt snapshot under %s" % root, file=sys.stderr)
        return 2
    doc = {"rev": REV, "what": "per recorded 3.17.2 arm spawn: sha256 and length of systemPrompt[0] (U22 H2)",
           "records": records}
    with open(FIXTURE, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({k: v for k, v in doc.items() if k != "records"}, sort_keys=True)[:-1]
                 + ', "records": [\n' + ",\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n]}\n")
    print("%d records -> %s" % (len(records), FIXTURE))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
