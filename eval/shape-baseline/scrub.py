#!/usr/bin/env python3
"""Remove machine-identifying strings from every NON-raw file of a run directory (raw/ is local, git-ignored).

    python3 eval/shape-baseline/scrub.py <run-dir>

Replaces: fixture path -> <FIXTURE>, arm export path -> <ARM>, scratch work dir -> <WORK>, home -> <HOME>,
the session id -> <SESSION>, any e-mail address -> <REDACTED>. Paths are matched in both their /tmp and
/private/tmp spellings. Reads the strings from raw/local.json; older pilot dirs that still carry them in
meta.json are migrated first. Idempotent.
"""
import json, os, re, sys

run = sys.argv[1].rstrip("/")
raw = os.path.join(run, "raw")
lp, mp = os.path.join(raw, "local.json"), os.path.join(run, "meta.json")
local = json.load(open(lp)) if os.path.exists(lp) else {}
if os.path.exists(mp):
    meta = json.load(open(mp, encoding="utf-8"))
    moved = False
    for k in ("plugin_dir", "session", "fixture", "machine", "cwd"):
        if k in meta:
            local.setdefault("fixture" if k == "cwd" else k, meta.pop(k))
            moved = True
    if moved:
        json.dump(meta, open(mp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        os.makedirs(raw, exist_ok=True)
        json.dump(local, open(lp, "w"), indent=1)
if os.path.exists(os.path.join(run, "settings.json")):
    os.replace(os.path.join(run, "settings.json"), os.path.join(raw, "settings.json"))

pairs = []
for key, tag in (("fixture", "<FIXTURE>"), ("plugin_dir", "<ARM>"), ("fixture_src", "<ARM-SRC>"), ("work", "<WORK>")):
    v = local.get(key)
    if v:
        variants = {v, os.path.realpath(v), v.replace("/private/tmp/", "/tmp/"), re.sub(r"^/tmp/", "/private/tmp/", v)}
        pairs += [(x, tag) for x in variants]
pairs.append((os.path.expanduser("~"), "<HOME>"))
if local.get("session"):
    pairs.append((local["session"], "<SESSION>"))
pairs.sort(key=lambda p: -len(p[0]))
email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?")
keep = {"eval@local"}
n = 0
for dirpath, dirs, files in os.walk(run):
    dirs[:] = [d for d in dirs if d != "raw"]
    for f in files:
        p = os.path.join(dirpath, f)
        try:
            text = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        new = text
        for a, b in pairs:
            new = new.replace(a, b)
        new = re.sub(r"/(?:private/)?tmp/claude-\d+/[^\s\"'\\,)\]]*", "<SCRATCH>", new)
        new = re.sub(r"/Users/[^/\s\"'\\]+", "<HOME>", new)
        new = email.sub(lambda m: m.group(0) if m.group(0) in keep or m.group(0).endswith("@local") else "<REDACTED>", new)
        if new != text:
            open(p, "w", encoding="utf-8").write(new)
            n += 1
print(f"scrubbed {n} file(s) under {run}")
