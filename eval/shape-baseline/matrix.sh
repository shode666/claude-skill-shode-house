#!/usr/bin/env bash
# Sequential matrix driver for one arm/distribution of protocol shape-baseline-v1. Resumable: re-invoke with the same args.
#   bash eval/shape-baseline/matrix.sh <arm-id> <distribution> <plugin-dir> <out-root>
# Env as run.sh, plus UTIL_MAX (default 0.80): before each run the latest rate_limit_event under <out-root> is read;
# 5-hour utilisation >= UTIL_MAX in a window that has not reset -> exit 5 (resume later with the same command).
# A slot whose run is UNSCORABLE is re-run into r<k>.retry<n>; the invalid run is kept. An infra result stops the batch (exit 5).
set -u
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
arm="${1:?}"; dist="${2:?}"; plugin="${3:?}"; root="${4:?}"
UTIL_MAX="${UTIL_MAX:-0.80}"
"$SB_HERE/check-freeze.sh" || sb_die "harness differs from eval/shape-baseline/FREEZE.sha256"
mkdir -p "$root/controls"
[ -d "$root/controls/noplugin" ] || bash "$SB_HERE/control.sh" "$root/controls/noplugin" "$WORK" || sb_die "control failed"
[ -d "$root/controls/$dist" ] || bash "$SB_HERE/control.sh" "$root/controls/$dist" "$WORK" "$plugin" || sb_die "control failed"
for c in noplugin "$dist"; do python3 "$SB_HERE/scrub.py" "$root/controls/$c" > /dev/null; done
plan="$(python3 -c '
import json,sys
for s in json.load(open(sys.argv[1]))["scenarios"]:
    for k in range(1, s["n"]+1): print(s["id"], k)' "$SB_HERE/scenarios.json")"
while read -r id k; do
  state="$(python3 - "$root" "$id" "$k" <<'PY'
import glob, json, os, sys
root, sid, k = sys.argv[1:4]
dirs = sorted(glob.glob(os.path.join(root, sid, f"r{k}")) + glob.glob(os.path.join(root, sid, f"r{k}.retry*")))
for d in dirs:
    try:
        if json.load(open(os.path.join(d, "score.json")))["verdict"] != "UNSCORABLE":
            print("done"); sys.exit()
    except (OSError, ValueError, KeyError):
        pass
print(k if not dirs else f"{k}.retry{len(dirs)}")
PY
)"
  [ "$state" = done ] && continue
  gate="$(python3 - "$root" "$UTIL_MAX" <<'PY'
import glob, json, os, sys, time
files = sorted(glob.glob(os.path.join(sys.argv[1], "**", "raw", "run.jsonl"), recursive=True), key=os.path.getmtime)
last = None
for f in files[-3:]:
    for line in open(f, encoding="utf-8"):
        if '"rate_limit_event"' in line:
            try:
                last = json.loads(line)["rate_limit_info"]
            except (ValueError, KeyError):
                pass
if not last:
    print("go unknown"); sys.exit()
w = (last.get("unifiedWindows") or {}).get("five_hour") or {}
u, reset = w.get("utilization", 0), w.get("resetsAt", 0)
wk = ((last.get("unifiedWindows") or {}).get("seven_day") or {}).get("utilization", 0)
print(("stop" if (u >= float(sys.argv[2]) and reset > time.time()) or wk >= 0.9 else "go"), u, reset, wk)
PY
)"
  case "$gate" in stop*) echo "== PAUSE before $id r$state: rate window ($gate). Re-invoke the same command after the reset."; exit 5 ;; esac
  bash "$SB_HERE/run.sh" "$arm" "$dist" "$plugin" "$id" "$state" "$root" || exit 3
  v="$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["verdict"],"|",";".join(d["invalid"]))' "$root/$id/r$state/score.json" 2>/dev/null || echo "UNSCORABLE | no score")"
  echo "   verdict: $v  (gate was: $gate)"
  case "$v" in UNSCORABLE*) echo "== STOP after $id r$state: unscorable run ($v). Inspect, then re-invoke to re-run the slot."; exit 5 ;; esac
done <<< "$plan"
python3 "$SB_HERE/summarize.py" "$root"
echo "== matrix complete: $root"
