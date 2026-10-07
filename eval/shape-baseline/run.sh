#!/usr/bin/env bash
# One live run of protocol shape-baseline-v1.
#   bash eval/shape-baseline/run.sh <arm-id> <distribution> <plugin-dir> <scenario-id> <rep> <out-root>
# Env: CLAUDE_BIN · FIXTURE_SRC (clean export of 1bc8174) · WORK (scratch dir for fixtures, outside any repo)
#      MAIN_MODEL (default sonnet) · EFFORT (default medium) · ROLE_MAP (default role-map.<arm-id>.json)
# Rules: one NEW directory per run (an existing one is refused) · every started run is kept and scored · a run is
# never retried to change its verdict · the runner records, metrics.py measures, score.py judges.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
arm="${1:?arm id}"; dist="${2:?distribution: generated|source}"; plugin="${3:?plugin dir}"; id="${4:?scenario}"; rep="${5:?rep}"; root="${6:?out root}"
: "${FIXTURE_SRC:?FIXTURE_SRC = clean export of 1bc8174}" "${WORK:?WORK = scratch dir}"
ROLE_MAP="${ROLE_MAP:-$SB_HERE/role-map.$arm.json}"
[ -f "$ROLE_MAP" ] || sb_die "no role map: $ROLE_MAP"
plugin="$(cd "$plugin" && pwd -P)" || sb_die "bad plugin dir"
[ -f "$plugin/.claude-plugin/plugin.json" ] || sb_die "no .claude-plugin/plugin.json under $plugin"
case "$plugin/" in "$(cd "$SB_HERE/../.." && pwd -P)"/*) sb_die "plugin dir is inside the working tree; use a clean export" ;; esac
out="$root/$id/r$rep"
[ -e "$out" ] && sb_die "refuse: $out exists (one new directory per run)"
mkdir -p "$out/raw" "$WORK"; out="$(cd "$out" && pwd -P)"

python3 - "$SB_HERE/scenarios.json" "$id" "$out/prompt.txt" "$out/limits.env" <<'PY' || sb_die "scenario $id not found"
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
s = next(x for x in d["scenarios"] if x["id"] == sys.argv[2])
open(sys.argv[3], "x", encoding="utf-8").write(s["prompt"])
lim = {**d["defaults"], **s.get("limits", {})}
open(sys.argv[4], "x").write("TURNS=%s\nBUDGET=%s\nTIMEOUT_S=%s\n" % (lim["max_turns"], lim["max_budget_usd"], lim["timeout_s"]))
PY
. "$out/limits.env"

fix="$(mktemp -d "$WORK/fx-$id-r$rep.XXXXXX")"
fixture_sha="$(bash "$SB_HERE/fixture.sh" "$fix" "$id" "$FIXTURE_SRC" 2> "$out/raw/fixture.log" | tail -1)" || sb_die "fixture build failed: $out/raw/fixture.log"
sid="$(python3 -c 'import uuid;print(uuid.uuid4())')"
sb_settings "$out/raw/settings.json" "$out/raw/snap.jsonl" "$plugin"
plugin_tree_sha="$(cd "$plugin" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256 | cut -d' ' -f1)"

start="$(sb_utc)"; t0=$(date +%s)
echo "== $start $arm/$dist $id r$rep model=$MAIN_MODEL effort=$EFFORT turns=$TURNS budget=$BUDGET -> $out"
rc=0
sb_launch "$fix" "$out" "$out/prompt.txt" "$sid" "$TURNS" "$BUDGET" "$TIMEOUT_S" --settings "$out/raw/settings.json" --plugin-dir "$plugin" || rc=$?
end="$(sb_utc)"; secs=$(( $(date +%s) - t0 ))

git -C "$fix" status --porcelain -uall > "$out/run.files" 2>&1
git -C "$fix" diff > "$out/run.diff" 2>&1
git -C "$fix" log --oneline > "$out/run.gitlog" 2>&1
sb_collect_transcript "$fix" "$sid" "$out" || true

M_OUT="$out" M_ARM="$arm" M_DIST="$dist" M_PLUGIN="$plugin" M_TREE="$plugin_tree_sha" M_ID="$id" M_REP="$rep" M_SID="$sid" \
M_FIX="$fix" M_FSHA="$fixture_sha" M_START="$start" M_END="$end" M_SECS="$secs" M_RC="$rc" M_MODEL="$MAIN_MODEL" M_EFFORT="$EFFORT" \
M_CLI="$("$CLAUDE_BIN" --version 2>/dev/null | head -1)" M_TURNS="$TURNS" M_BUDGET="$BUDGET" M_HERE="$SB_HERE" M_SRC="$FIXTURE_SRC" \
python3 - <<'PY'
import hashlib, json, os, platform
e = os.environ
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
here, out = e["M_HERE"], e["M_OUT"]
manifest = json.load(open(os.path.join(e["M_PLUGIN"], ".claude-plugin", "plugin.json")))
json.dump({
    "protocol": "shape-baseline-v1", "arm": e["M_ARM"], "distribution": e["M_DIST"], "scenario": e["M_ID"], "rep": e["M_REP"],
    "slot": int(e["M_REP"].split(".")[0]),
    "plugin_manifest_version": manifest.get("version"), "plugin_tree_sha256": e["M_TREE"], "fixture_head": e["M_FSHA"],
    "start": e["M_START"], "end": e["M_END"], "seconds": int(e["M_SECS"]), "claude_exit": int(e["M_RC"]),
    "main_model_requested": e["M_MODEL"], "effort": e["M_EFFORT"], "cli_version": e["M_CLI"],
    "max_turns": int(e["M_TURNS"]), "max_budget_usd": float(e["M_BUDGET"]),
    "prompt_bytes": os.path.getsize(os.path.join(out, "prompt.txt")),
    "sha256": {k: sha(os.path.join(here, k)) for k in ("scenarios.json", "lib.sh", "run.sh", "fixture.sh", "metrics.py", "score.py",
                                                       "hook-snap.py", "scrub.py", "role-policy.json", "role-map.%s.json" % e["M_ARM"])},
    "prompt_sha256": sha(os.path.join(out, "prompt.txt")),
}, open(os.path.join(out, "meta.json"), "x", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump({"plugin_dir": e["M_PLUGIN"], "session": e["M_SID"], "fixture": e["M_FIX"], "machine": platform.platform(),
           "work": os.path.dirname(e["M_FIX"]), "fixture_src": e["M_SRC"]}, open(os.path.join(out, "raw", "local.json"), "x"), indent=1)
PY
python3 "$SB_HERE/metrics.py" "$out" --controls "$root/controls" --plugin-dir "$plugin" --role-map "$ROLE_MAP" > "$out/metrics.txt" 2>&1 || echo "!! metrics failed, see $out/metrics.txt" >&2
python3 "$SB_HERE/score.py" "$out" --plugin-dir "$plugin" --role-map "$ROLE_MAP" > "$out/score.txt" 2>&1; src=$?
python3 "$SB_HERE/scrub.py" "$out" || echo "!! scrub failed for $out" >&2
echo "== $end $id r$rep done: claude exit=$rc, ${secs}s, score exit=$src (0 PASS / 1 FAIL / 2 UNSCORABLE / 4 NEEDS-HUMAN-READ)"
cat "$out/metrics.txt" | head -3
exit 0
