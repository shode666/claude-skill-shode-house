#!/usr/bin/env bash
# route.sh -- Milestone B declarative routing resolver (bd: shode-roadmap/C-B1)
#
# scripts/route.sh <request.json>
#
# Reads references/registry/capabilities.json + references/registry/routes.json
# (both transcribed verbatim from existing routing prose -- see each file's own
# `_source`/`_comment` field; no new rule invented here, ROADMAP-runtime-10.md
# SS 3.1/3.2/3.3) and resolves a request to {primary, required[], phases[]} so
# Oliver executes the routing result instead of re-deriving it from prose.
#
# request.json shape (all keys optional):
#   {
#     "capability": "production-code",   -- looked up in capabilities.json;
#                                            default "production-code" (Dave)
#     "tags":  ["payment", "kyc"],        -- matched against routes[].when.any
#     "text":  "free text description",  -- substring-matched too (case-insens.)
#     "pii": true, "frontend": true, ...  -- matched against routes[].when.<flag>
#   }
#
# Output (stdout, one compact JSON line):
#   {"primary":"developer","required":["fintech-expert"],"phases":["phase_0","phase_1b","phase_3b"]}
#
# Deps: bash + jq only (ADR-C3 style -- no python3 in this hot path).

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAPS="${ROUTE_CAPABILITIES:-$SELF_DIR/../references/registry/capabilities.json}"
ROUTES="${ROUTE_ROUTES:-$SELF_DIR/../references/registry/routes.json}"
TRANSITIONS="${ROUTE_TRANSITIONS:-$SELF_DIR/../references/state-machine/transitions.json}"

die()   { printf 'route.sh: %s\n' "$*" >&2; exit 1; }
usage() { printf 'usage: route.sh <request.json>\n' >&2; }

[ $# -eq 1 ] || { usage; die "exactly one argument required"; }
REQ="$1"

[ -f "$REQ" ]   || die "request file not found: $REQ"
jq empty "$REQ" >/dev/null 2>&1 || die "$REQ is not valid JSON"
[ -f "$CAPS" ]   || die "capability registry not found: $CAPS"
[ -f "$ROUTES" ] || die "route registry not found: $ROUTES"
[ -f "$TRANSITIONS" ] || die "state-machine transitions not found: $TRANSITIONS"
jq empty "$CAPS"   >/dev/null 2>&1 || die "$CAPS is not valid JSON"
jq empty "$ROUTES" >/dev/null 2>&1 || die "$ROUTES is not valid JSON"
jq empty "$TRANSITIONS" >/dev/null 2>&1 || die "$TRANSITIONS is not valid JSON"

# canonical phase order for stable, human-diffable output -- read straight from the
# state machine's own `.states` (references/state-machine/transitions.json) instead of
# a second hardcoded copy (bd: shode-roadmap/C-A6 iter0 -- the old inline literal used a
# phase_0/phase_1a/... vocabulary that had drifted from the state machine's actual node
# ids ('0-discover', '1a-spec', ...), which is the single source of truth per CLAUDE.md
# 'Repo'; sourcing it here means route.sh can never drift from it again).
PHASE_ORDER="$(jq -c '.states' "$TRANSITIONS")"

CAPABILITY=$(jq -r '.capability // "production-code"' "$REQ")
PRIMARY=$(jq -r --arg c "$CAPABILITY" '.capabilities[$c].owner // empty' "$CAPS")
[ -n "$PRIMARY" ] || die "unknown capability '$CAPABILITY' -- not declared in $CAPS (no guessing; add it there first)"

# one jq pass does the when-matching + aggregation -- pure data transform, no
# reason to spawn jq once per route in a bash loop.
jq -n \
  --slurpfile req "$REQ" \
  --slurpfile routesf "$ROUTES" \
  --arg primary "$PRIMARY" \
  --argjson phase_order "$PHASE_ORDER" '
  ($req[0]) as $r
  | ($routesf[0].routes) as $routes
  | (($r.tags // []) | map(ascii_downcase)) as $tags_lc
  | ($r.text // "" | ascii_downcase) as $text_lc
  | (
      $routes
      | map(
          . as $route
          | ($route.when | to_entries) as $conds
          | (
              $conds
              | all(
                  .key as $k | .value as $v
                  | if $k == "any" then
                      ($v | any(. as $item
                                 | ($tags_lc | index($item | ascii_downcase)) != null
                                   or ($text_lc | contains($item | ascii_downcase))))
                    else
                      (($r[$k] // false) == $v)
                    end
                )
            ) as $matched
          | if $matched then $route else empty end
        )
    ) as $matched_routes
  | ($matched_routes | map(.require[]) | unique) as $required_all
  | ($required_all | map(select(. != $primary))) as $required
  | ($matched_routes | map(.phases[]) | unique) as $phases_all
  | ($phase_order | map(select(. as $p | $phases_all | index($p) != null))) as $phases
  | {primary: $primary, required: $required, phases: $phases}
  '
