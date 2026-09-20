#!/usr/bin/env bash
# P0-probe-baseline / FR-P1-4: routing probes, sequential, N=1, every run kept.
#   bash eval/run-probes.sh [model=sonnet] [out-dir]
#   PROBE_IDS="P01 P02" bash eval/run-probes.sh sonnet <new-dir>   subset rerun into a NEW directory
#   PROBE_IDS=all = every kind:"probe" id without a `not_applicable` note
#   SUMMARY.tsv: id exit route first_skill first_agent seconds (route = first skill-or-agent, whichever came first)
#   PLUGIN_REF=baseline-3.17 bash eval/run-probes.sh  test that ref (git archive) instead of the working tree
# default ids: P01..P15 · default out-dir: outputs/eval-3.17/probes/<model>-<UTC timestamp>/ (must not exist)
# layout: <out-dir>/<id>/{run.jsonl,run.files,meta.json,score.txt,tools-seen.txt,...} + <out-dir>/SUMMARY.tsv
# exit 0 = every probe scored 0/1 · 2 = at least one UNSCORABLE/refused (a FAIL is data, not a script error)
. "$(dirname "${BASH_SOURCE[0]}")/run-lib.sh"
MODEL="${1:-sonnet}"
OUT="${2:-$REPO/outputs/eval-3.17/probes/$MODEL-$(date -u +%Y%m%dT%H%M%SZ)}"
[ -e "$OUT" ] && die "refuse: $OUT already exists"
IDS="${PROBE_IDS:-P01 P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15}"
if [ "$IDS" = all ]; then
  IDS="$(python3 -c 'import json,sys;print(" ".join(s["id"] for s in json.load(open(sys.argv[1],encoding="utf-8"))["scenarios"] if s.get("kind")=="probe" and not s.get("not_applicable")))' "$SCENARIOS")"
fi
preflight
mkdir -p "$OUT" || die "cannot create $OUT"
OUT="$(cd "$OUT" && pwd -P)"
printf 'id\texit\troute\tfirst_skill\tfirst_agent\tseconds\n' > "$OUT/SUMMARY.tsv"
BAD=0
for ID in $IDS; do
  FIRST_ROUTE="-" FIRST_SKILL="-" FIRST_AGENT="-" SECONDS_TAKEN=0
  run_one "$ID" "$MODEL" "$OUT/$ID"; RC=$?
  [ "$RC" -ge 2 ] && BAD=$((BAD + 1))
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$ID" "$RC" "$FIRST_ROUTE" "$FIRST_SKILL" "$FIRST_AGENT" "$SECONDS_TAKEN" >> "$OUT/SUMMARY.tsv"
done
echo "--- SUMMARY.tsv ($OUT)"; cat "$OUT/SUMMARY.tsv"
echo "SUMMARY probes model=$MODEL plugin=${PLUGIN_REF:-WORKTREE}@${PLUGIN_SHA:0:7} runs=$(($(wc -l < "$OUT/SUMMARY.tsv") - 1)) unscorable_or_refused=$BAD dir=$OUT"
[ "$BAD" = 0 ] || exit 2
exit 0
