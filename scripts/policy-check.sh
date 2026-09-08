#!/usr/bin/env bash
# policy-check.sh -- Milestone B executable policy engine (bd: shode-roadmap/C-B1)
#
# scripts/policy-check.sh <bd-id>
#
# Reads .enforcement-map.json (v3.13, ~20 rules) and reports, per rule, one of:
#   PASS <id>              runtime evidence found for THIS bd, rule satisfied
#   FAIL <id> -- <reason>  runtime evidence found for THIS bd, rule violated
#   SKIP <id> -- <reason>  cannot be verified from this bd's own runtime
#                          artifact -- NEVER silently PASS (ROADMAP-runtime-10.md
#                          SS 4: "rule ที่ verify ไม่ได้ใน runtime ⇒ SKIP")
#
# Evidence source = outputs/<bd-id>/**/*.md (Handoff Contract artifact
# convention -- shode-house-discipline SS Handoff Contract: "Producer เขียน
# artifact ลงไฟล์ -> outputs/<bd-id>/<NN>-<agent>-<phase>.md"). Only rules whose
# *documented meaning* is directly checkable from that artifact's own text get
# a real PASS/FAIL:
#   - anti-puppet : shode-house-deliverable/SKILL.md's Output contract point 3
#     ("No placeholder" -- TBD / <fill this> without an OPEN QUESTION mark)
#   - redact      : CLAUDE.md SS Agents "Redact ก่อน paste" (secret-shaped token
#     pasted into an artifact without <REDACTED>)
# Every other rule's `.verification` tag (fixture / ci:* / mutation / close-gate
# / output-style-test / citation fixture / a11y fixture / ...) names a check
# this script has no way to run locally (recorded-transcript scorer harness,
# a live CI job, a live mutation-testing run, human sign-off judgement) -- those
# are SKIP with the concrete reason, not guessed at.
#
# Deps: bash + jq only (ADR-C3 style -- no python3 in this hot path).

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${POLICYCHECK_ROOT:-$PWD}"
MAP="${POLICYCHECK_MAP:-$SELF_DIR/../.enforcement-map.json}"

PASS_N=0
FAIL_N=0
SKIP_N=0

die()   { printf 'policy-check.sh: %s\n' "$*" >&2; exit 1; }
usage() { printf 'usage: policy-check.sh <bd-id>\n' >&2; }

[ $# -eq 1 ] || { usage; die "exactly one argument required"; }
BD="$1"

[ -f "$MAP" ] || die "enforcement map not found: $MAP"
jq empty "$MAP" >/dev/null 2>&1 || die "$MAP is not valid JSON"

ARTIFACT_DIR="$ROOT/outputs/$BD"

artifact_files() {
  [ -d "$ARTIFACT_DIR" ] || return 0
  find "$ARTIFACT_DIR" -type f -name '*.md' 2>/dev/null
}

has_artifacts() { [ -n "$(artifact_files)" ]; }

# anti-puppet real check -- shode-house-deliverable/SKILL.md SS Output contract
# point 3 "No placeholder": ห้าม TBD / <fill this> โดยไม่ mark เป็น OPEN QUESTION
check_placeholder() {
  local f hit=0
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if grep -Eq '(^|[^A-Za-z])TBD([^A-Za-z]|$)|<fill this>' "$f" 2>/dev/null \
       && ! grep -Eq 'OPEN QUESTION' "$f" 2>/dev/null; then
      hit=1
    fi
  done < <(artifact_files)
  [ "$hit" -eq 0 ]
}

# redact real check -- CLAUDE.md SS Agents "Redact ก่อน paste": secret-shaped
# token ที่ paste ลง artifact ต้องเป็น <REDACTED>
check_redact() {
  local f hit=0
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if grep -Eq 'sk-[A-Za-z0-9]{16,}|AKIA[A-Z0-9]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[Bb]earer [A-Za-z0-9._-]{10,}' "$f" 2>/dev/null; then
      hit=1
    fi
  done < <(artifact_files)
  [ "$hit" -eq 0 ]
}

report() {
  local verdict="$1" id="$2" reason="${3:-}"
  case "$verdict" in
    PASS) PASS_N=$((PASS_N + 1)); printf 'PASS %s\n' "$id" ;;
    FAIL) FAIL_N=$((FAIL_N + 1)); printf 'FAIL %s -- %s\n' "$id" "$reason" ;;
    SKIP) SKIP_N=$((SKIP_N + 1)); printf 'SKIP %s -- %s\n' "$id" "$reason" ;;
  esac
}

# generic SKIP reason keyed off the rule's own `verification` field -- never
# invents a bd-specific signal that doesn't actually exist
skip_reason_for() {
  case "$1" in
    *ci:*)              printf 'verification="%s" is a CI job step (.github/workflows/ci.yml) -- not reproducible from a single bd'"'"'s local artifact' "$1" ;;
    *fixture*)          printf 'verification="%s" needs the recorded-transcript scorer harness (eval/) -- no such fixture is wired to bd artifact yet' "$1" ;;
    mutation)           printf 'verification="mutation" needs a live mutation-testing run (Chris kill-rate) -- not derivable from a static bd artifact' ;;
    close-gate)         printf 'verification="close-gate" is a phase-exit sign-off judgement call -- not mechanically derivable from artifact presence alone' ;;
    output-style-test)  printf 'verification="output-style-test" needs a live main-session transcript -- no bd-scoped artifact carries this' ;;
    *)                  printf 'verification="%s" has no bd-scoped runtime check implemented yet' "$1" ;;
  esac
}

while IFS=$'\t' read -r id verification; do
  [ -z "$id" ] && continue
  case "$id" in
    anti-puppet)
      if ! has_artifacts; then
        report SKIP "$id" "no outputs/$BD/**/*.md artifact found for this bd yet"
      elif check_placeholder; then
        report PASS "$id"
      else
        report FAIL "$id" "found TBD / <fill this> placeholder in outputs/$BD without an OPEN QUESTION mark"
      fi
      ;;
    redact)
      if ! has_artifacts; then
        report SKIP "$id" "no outputs/$BD/**/*.md artifact found for this bd yet"
      elif check_redact; then
        report PASS "$id"
      else
        report FAIL "$id" "found an unredacted secret-shaped token in outputs/$BD (see CLAUDE.md SS Agents Redact)"
      fi
      ;;
    *)
      report SKIP "$id" "$(skip_reason_for "$verification")"
      ;;
  esac
done < <(jq -r '.rules[] | [.id, .verification] | @tsv' "$MAP")

printf '\n== %d PASS, %d FAIL, %d SKIP (%d rules total) ==\n' "$PASS_N" "$FAIL_N" "$SKIP_N" "$((PASS_N + FAIL_N + SKIP_N))"
[ "$FAIL_N" -eq 0 ]
