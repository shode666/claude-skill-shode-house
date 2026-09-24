#!/usr/bin/env bash
# After-arm diff restriction: between BASE and AFTER the plugin may differ ONLY in the `description:` of
# skills/*/*/SKILL.md (plus the `version` line of .claude-plugin/{plugin,marketplace}.json).
#   bash eval/check-arm-diff.sh BASE AFTER [PROMPT_SET]
#   PROMPT_SET = directory of probe .md files (default eval/prompts/probes, only P28+ = the public paraphrases)
#                or a scenarios JSON with inline `prompt_text` (the held-out set; run by the validator only)
#   ARM_SCOPE=description  (default, unset = this)  the rule above, unchanged.
#   ARM_SCOPE=floor        the dispatch-floor arm of eval/PROBE-GATE-floor.md: the ONLY files that may differ are
#                          output-styles/oliver.md and its two generated copies
#                          (plugins/shode-house/output-styles/oliver.md,
#                           plugins/shode-house/knowledge/output-styles/oliver.md), which must be byte-identical to
#                          the root file in AFTER. Modifications only, and the difference must be in CONTENT: the root
#                          file's bytes must differ between the arms, and a mode-only (chmod) row is refused, not
#                          counted as an arm difference. NOTHING else may differ -- not a skill
#                          description, not the `version` line, not an agent, not a hook. Files outside the diff
#                          SCOPE below (.enforcement-map.json, docs/**, .workflow-scenario-budget) are not shipped
#                          in the plugin and are, as always, not inspected by this script.
# exit 0 = allowed · 1 = violation (listed) · 2 = usage / bad ref.  CHECK_ROOT overrides the repo root (tests).
ROOT="${CHECK_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
[ $# -ge 2 ] || { echo "usage: check-arm-diff.sh BASE AFTER [PROMPT_SET]" >&2; exit 2; }
case "${ARM_SCOPE:-description}" in description|floor) ;; *) echo "check-arm-diff: unknown ARM_SCOPE '$ARM_SCOPE' (description|floor)" >&2; exit 2 ;; esac
exec python3 - "$ROOT" "$1" "$2" "${3:-}" "${ARM_SCOPE:-description}" <<'PY'
import fnmatch, glob, json, os, re, subprocess, sys
root, base_ref, after_ref, prompt_set, scope = sys.argv[1:6]
SCOPE = ["agents", "commands", "skills", "hooks", "references", "output-styles", ".claude-plugin",
         ".mcp.json", "CLAUDE.md", "AGENTS.md", ".claude", ".agents", "plugins"]  # git archive ships the whole tree
VERSIONED = {".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"}


def git(*args, check=True):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if check and p.returncode:
        sys.stderr.write(p.stderr); sys.exit(2)
    return p.stdout


FLOOR_ROOT = "output-styles/oliver.md"
FLOOR_COPIES = ["plugins/shode-house/output-styles/oliver.md",
                "plugins/shode-house/knowledge/output-styles/oliver.md"]
FLOOR_ALLOWED = [FLOOR_ROOT] + FLOOR_COPIES

base, after = (git("rev-parse", "--verify", r + "^{commit}").strip() for r in (base_ref, after_ref))
print(f"BASE  {base_ref} = {base}\nAFTER {after_ref} = {after}\nSCOPE {scope}")
bad, changed, floor = [], [], []


def split(text):
    """-> (frontmatter blocks {key: raw lines}, key order, body) ; frontmatter = between the first two `---` lines."""
    lines = text.split("\n")
    marks = [i for i, ln in enumerate(lines) if ln.strip() == "---"][:2]
    if len(marks) < 2 or marks[0] != 0:
        return None
    blocks, order, key = {}, [], None
    for ln in lines[1:marks[1]]:
        m = re.match(r"^([A-Za-z_][\w-]*):", ln)
        if m:
            key = m.group(1); order.append(key); blocks[key] = []
        if key is None:
            blocks.setdefault("", []).append(ln)
        else:
            blocks[key].append(ln)
    return blocks, order, "\n".join(lines[marks[1]:])


for row in git("diff", "--no-renames", "--name-status", base, after, "--", *SCOPE).splitlines():
    status, path = row.split("\t", 1)
    if status != "M":
        bad.append(f"{status} {path}: only modifications are allowed (no add/delete/rename)"); continue
    old, new = git("show", f"{base}:{path}"), git("show", f"{after}:{path}")
    if scope == "floor":
        if path not in FLOOR_ALLOWED:
            bad.append(f"M {path}: ARM_SCOPE=floor permits only {' , '.join(FLOOR_ALLOWED)}")
        elif old == new:
            # a mode-only row (chmod) is still `M` in --name-status: it is not an arm difference.
            bad.append(f"M {path}: content identical between the arms (mode-only change is not an arm difference)")
        else:
            floor.append(path)
        continue
    if path in VERSIONED:
        diff = [(a, b) for a, b in zip(old.split("\n"), new.split("\n")) if a != b]
        if len(old.split("\n")) != len(new.split("\n")) or any(not re.match(r'^\s*"version"\s*:', a) or not re.match(r'^\s*"version"\s*:', b) for a, b in diff):
            bad.append(f"M {path}: only the \"version\" line may change")
        continue
    if not fnmatch.fnmatchcase(path, "skills/*/*/SKILL.md") or path.count("/") != 3:
        bad.append(f"M {path}: outside skills/*/*/SKILL.md"); continue
    a, b = split(old), split(new)
    if a is None or b is None:
        bad.append(f"M {path}: frontmatter not parseable"); continue
    if a[2] != b[2]:
        bad.append(f"M {path}: body changed (only the description may change)")
    if a[1] != b[1]:
        bad.append(f"M {path}: frontmatter keys added/removed/reordered {a[1]} -> {b[1]}")
    for key in set(a[0]) | set(b[0]):
        if key != "description" and a[0].get(key) != b[0].get(key):
            bad.append(f"M {path}: frontmatter `{key or '(preamble)'}` changed")
    if a[0].get("description") != b[0].get("description"):
        changed.append((path, "\n".join(b[0].get("description", []))))

if scope == "floor":
    # the generated copies are byte-identical to the root file (scripts/pack-team.py); an arm where they are not
    # is not one logical change.
    if git("show", f"{base}:{FLOOR_ROOT}") == git("show", f"{after}:{FLOOR_ROOT}"):
        bad.append(f"ARM_SCOPE=floor: {FLOOR_ROOT} has identical CONTENT in both arms (nothing to measure)")
    want = git("show", f"{after}:{FLOOR_ROOT}")
    for rel in FLOOR_COPIES:
        if git("show", f"{after}:{rel}") != want:
            bad.append(f"{rel}: not byte-identical to {FLOOR_ROOT} in AFTER (run `make pack`)")
    print(f"floor files changed: {len(floor)} | prompts linted: 0")
    print("\n".join(bad) if bad else "arm diff OK: floor-only")
    sys.exit(1 if bad else 0)

# step 3: leak lint of each NEW description against the probe prompts
prompts = {}
if prompt_set and os.path.isfile(prompt_set):
    data = json.load(open(prompt_set, encoding="utf-8"))
    for s in (data["scenarios"] if isinstance(data, dict) else data):
        if isinstance(s.get("prompt_text"), str):
            prompts[s.get("id", "?")] = s["prompt_text"]
else:
    folder = prompt_set or os.path.join(root, "eval/prompts/probes")
    for p in sorted(glob.glob(os.path.join(folder, "*.md"))):
        name = os.path.basename(p)[:-3]
        m = re.search(r"^## Prompt[^\n]*\n+```[^\n]*\n(.*?)\n```", open(p, encoding="utf-8").read(), re.S | re.M)
        number = re.fullmatch(r"P(\d+)", name)
        if m and (prompt_set or (number and int(number.group(1)) >= 28)):
            prompts[name] = m.group(1)
thai = lambda t: re.findall(r"[฀-๿]+", t)
words = lambda t: re.findall(r"[a-z0-9]+", t.lower())
for path, desc in changed:
    grams = {run[i:i + 8] for run in thai(desc) for i in range(len(run) - 7)}
    w = words(desc)
    triples = {tuple(w[i:i + 3]) for i in range(len(w) - 2)}
    for ident, text in prompts.items():
        hit = next((g for run in thai(text) for g in (run[i:i + 8] for i in range(len(run) - 7)) if g in grams), None)
        pw = words(text)
        hit3 = next((t for t in (tuple(pw[i:i + 3]) for i in range(len(pw) - 2)) if t in triples), None)
        if hit:
            bad.append(f"LEAK {path} ~ {ident}: shared Thai run >= 8 chars: {hit!r}")
        if hit3:
            bad.append(f"LEAK {path} ~ {ident}: 3 consecutive shared words: {' '.join(hit3)}")
print(f"changed descriptions: {len(changed)} | prompts linted: {len(prompts)}")
print("\n".join(bad) if bad else "arm diff OK: description-only")
sys.exit(1 if bad else 0)
PY
