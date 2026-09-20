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
# request.json shape:
#   {
#     "capability": "production-code",   -- REQUIRED, looked up in capabilities.json.
#                                            No default any more (bd: shode-house-5cs.2 --
#                                            used to silently fall back to "production-code"
#                                            i.e. Dave, which hid mis-routed/malformed
#                                            requests). Absent/null/empty = hard error.
#     "tags":  ["payment", "kyc"],        -- matched against routes[].when.any, EXACT
#                                            match (case-insensitive) per tag string
#     "text":  "free text description",  -- matched against routes[].when.any too, but
#                                            WORD-TOKEN match for ASCII keywords (never a
#                                            fragment inside another word -- "fix" no
#                                            longer matches inside "prefix") and substring
#                                            match for non-ASCII (e.g. Thai) keywords,
#                                            which have no ASCII word boundary to
#                                            tokenize on (bd: shode-house-5cs.2). A
#                                            single-word when.any item (incl. a hyphenated
#                                            one like "file-upload", "ai-agent",
#                                            "external-integration" -- iter1 F1) is checked
#                                            against $text_tokens, which keeps a
#                                            hyphen-joined run as ONE token so the literal
#                                            hyphenated keyword stays matchable. A when.any
#                                            item that contains a space (e.g. "fix
#                                            protocol") is an ADJACENT-PHRASE match against
#                                            $items instead -- its words must appear as
#                                            consecutive slots, in that order, not just
#                                            anywhere in text (iter1 F3 -- "anywhere"
#                                            AND-matching reintroduced false positives,
#                                            e.g. "in order to speed up trading of assets"
#                                            wrongly requiring trading-expert).
#
#                                            Phrase adjacency is defined POSITIVELY (bd:
#                                            shode-house-5cs.2 iter3b, correcting iter3's
#                                            "exactly one separator CHARACTER" rule against
#                                            the user's own authoritative spec, which iter3's
#                                            brief predated; whitespace-CLASS fix in iter3c,
#                                            see below): two phrase words are adjacent iff
#                                            the gap between them is EITHER (1) a run of
#                                            one-or-more WHITESPACE characters (ANY character
#                                            in the whitespace CLASS -- not an enumerated
#                                            list, see iter3c note -- any mix, any length) OR
#                                            (2) exactly one ASCII hyphen with no whitespace
#                                            on either side of it. $items is built by
#                                            scanning $text with
#                                            "[a-z0-9]+|[[:space:]]+|.", so every alnum run
#                                            is one WORD slot, every whitespace RUN (however
#                                            long, however mixed) collapses to one slot, and
#                                            every remaining single non-alnum,
#                                            non-whitespace character (colon, hyphen, comma,
#                                            em-dash's two hyphens individually, etc.) gets
#                                            its own one-character slot. is_separator then
#                                            accepts a slot iff it is either whitespace-only
#                                            (any length, since it is already a single
#                                            collapsed run) or the literal one-character
#                                            string "-". A hyphen with whitespace next to it
#                                            ("trading - order", "trading- order") never
#                                            collapses into the same slot as that whitespace
#                                            -- the scan's alternation always splits
#                                            whitespace runs and the hyphen into separate
#                                            slots -- so the gap occupies TWO-OR-MORE slots
#                                            and phrase_match's fixed $start+2*$j index
#                                            arithmetic still fails it, same as a colon or
#                                            an em-dash ("trading: order", "trading --
#                                            order") or a run of two-or-more hyphens
#                                            ("trading--order"). This is what lets "trading
#                                            order" (single space), "trading  order" /
#                                            "trading   order" (double/triple space --
#                                            iter3's residual defect, Oliver-measured: iter3
#                                            wrongly required an exact single separator
#                                            CHARACTER, so a bare whitespace run of 2+ was
#                                            rejected as if it were an em-dash), and
#                                            "trading\norder" / "trading\torder" / mixed
#                                            "trading \tsomething" all still match, while
#                                            "trading -- order" / "trading: order" / "trading
#                                            - order" still correctly do not. One disclosed,
#                                            non-regressing behavior change (carried
#                                            unchanged from iter3): a bare underscore
#                                            ("trading_order") does not bridge two phrase
#                                            words -- underscore is neither whitespace nor a
#                                            hyphen, so it is a boundary by the same rule
#                                            that makes a colon one; never covered by a
#                                            fixture, not part of the required matrix.
#
#                                            iter3c (bd: shode-house-5cs.2, Chris+Quinn
#                                            iter3b re-review, both axes independently):
#                                            iter3b's "whitespace" half of the rule was
#                                            still an ENUMERATED list -- exactly three
#                                            characters, "[ \t\n]" (space/tab/LF) -- so CR,
#                                            vertical tab, form feed, and every non-ASCII
#                                            whitespace codepoint (NBSP, ideographic space,
#                                            U+2028/U+2029, the U+2000-U+200A family) fell
#                                            through to the single-char "." alternative and
#                                            broke adjacency, same failure SHAPE as iter1's
#                                            missing-colon and iter2's missing-CR/VT/FF (a
#                                            hand-picked list, short by exactly the
#                                            characters nobody thought to enumerate) even
#                                            though the polarity differs each time. Fixed by
#                                            matching a whitespace character CLASS instead
#                                            of a list: "[[:space:]]" (Oniguruma POSIX
#                                            class, verified own-run to include the full
#                                            Unicode `White_Space` property -- space, tab,
#                                            LF, CR, VT, FF, NBSP, ideographic space,
#                                            U+2028, U+2029, the U+2000-U+200A family all
#                                            test true; zero-width characters, U+200B and
#                                            U+200E, correctly test false and so remain
#                                            boundaries, unchanged) in the same two places
#                                            the old three-character list lived: $items'
#                                            scan alternation and is_separator's test. Oliver's
#                                            ruling: ALL whitespace counts, Unicode
#                                            included -- NBSP arrives constantly from
#                                            copy-paste out of web pages/documents and
#                                            ideographic space arrives with CJK text;
#                                            treating either as a boundary would silently
#                                            under-match exactly the class of request this bd
#                                            exists to stop dropping. This closes the class by
#                                            construction rather than by enumeration -- a
#                                            whitespace character nobody has thought of yet
#                                            is still classified correctly, because it is not
#                                            named anywhere, a property is tested instead.
#
#                                            The FINAL word of a
#                                            phrase, and any standalone single-word ASCII
#                                            keyword, also accepts a regular plural: a
#                                            trailing "s" is stripped from both the keyword
#                                            and the candidate token before comparing
#                                            (length > 4, not a double-s word -- raised
#                                            from length > 3 in iter2 D2 after "this
#                                            refactor saps my energy" wrongly required
#                                            sap-expert: "saps" [4 chars] stemmed to "sap"
#                                            and collided with the unrelated 3-char keyword
#                                            "sap". Every when.any keyword was checked for
#                                            the same shape -- keywords of 4+ chars keep
#                                            full plural coverage since their plural is
#                                            always 5+ chars and still clears the new
#                                            floor [e.g. "trading order"/"insurance
#                                            claim"/"inventory stock" all still match their
#                                            plurals]; only the five 3-char-or-shorter
#                                            keywords -- "sap", "kyc", "mrp", "btp", "pms"
#                                            -- lose plural-stemming eligibility for their
#                                            candidate tokens. None of those five had a
#                                            fixture or requirement relying on stemming;
#                                            "mrp"/"mrps" (benign, same meaning) is the one
#                                            observed loss, accepted as the cost of closing
#                                            the "sap"/"saps" collision generally rather
#                                            than special-casing "sap" alone). Standing
#                                            policy (Oliver ruling, iter2, recorded here so a
#                                            future maintainer does not need this bd's
#                                            `outputs/` history to find it): this loss for
#                                            "mrp"/"kyc"/"btp" is ACCEPTED, permanently, as
#                                            the cost of closing the "sap"/"saps" collision
#                                            generally. If a plural acronym ever matters in
#                                            practice, the fix is to add that plural as its
#                                            own explicit `when.any` keyword in routes.json
#                                            (e.g. add "mrps" alongside "mrp") -- NEVER to
#                                            lower this length-4 threshold again, since that
#                                            reopens the exact "saps"->sap-expert collision
#                                            this floor exists to close. Irregular
#                                            plurals (e.g. "policy"/"policies") are still
#                                            NOT covered by this suffix rule -- pre-existing
#                                            gap, out of this bd's scope. Used to
#                                            disambiguate generic English words that were
#                                            false-positive-prone as single tokens (see
#                                            routes.json "_disambiguated" notes).
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

# bd: shode-house-5cs.2 -- absent/null/empty capability must be a loud error, not a
# silent fallback to "production-code" (Dave). Same `die` shape as the unknown-capability
# check right below, which was already correct.
CAPABILITY=$(jq -r 'if (has("capability") and (.capability != null) and (.capability != "")) then .capability else empty end' "$REQ")
[ -n "$CAPABILITY" ] || die "missing 'capability' in $REQ -- no default (no guessing who owns the request; set one explicitly, see $CAPS for valid values)"
PRIMARY=$(jq -r --arg c "$CAPABILITY" '.capabilities[$c].owner // empty' "$CAPS")
[ -n "$PRIMARY" ] || die "unknown capability '$CAPABILITY' -- not declared in $CAPS (no guessing; add it there first)"

# one jq pass does the when-matching + aggregation -- pure data transform, no
# reason to spawn jq once per route in a bash loop.
#
# bd: shode-house-5cs.2 -- `text` matching used to be raw jq contains() (substring),
# which false-positived on fragments inside other words ("fix" inside "prefix") and on
# generic English words used as single keywords ("policy" in "security policy doc").
# Fixed with word/token matching, reworked again in iter1 after 3-axis review FAIL,
# reworked a third time in iter2 after review found 3 new defects in iter1's own new
# mechanisms (D1/D2/D3), a fourth time in iter3 after review found the iter2 D1 fix itself
# was an enumerated blacklist of boundary punctuation (`[.!?,;\n]`) that both over-applied
# (bare newline) and under-applied (missed colon, em-dash), a fifth time in iter3b after
# Oliver measured that iter3's "exactly one separator CHARACTER" rule -- written against a
# brief that predated the user's own authoritative spec -- silently rejected a whitespace
# RUN of 2+ (double/triple space, common in ordinary prose) as if it were a multi-character
# punctuation break, and a sixth time in iter3c after Chris+Quinn (iter3b re-review, both
# axes independently) found iter3b's "whitespace" half was STILL an enumerated list of
# exactly three characters (space/tab/LF), so CR, VT, FF, and every non-ASCII whitespace
# codepoint fell through and broke adjacency -- see 18-dave-L1-implement-iter2.md,
# 21-quinn-L1-review-iter2.md, 23-dave-L1-implement-iter3.md, 28-chris-L1-review-iter3b.md,
# 29-quinn-L1-review-iter3b.md for the earlier history:
#   - phrase adjacency is defined POSITIVELY (iter3, corrected iter3b, whitespace half
#     re-fixed iter3c): two consecutive phrase words are adjacent iff the gap between them
#     is EITHER a run of one-or-more WHITESPACE characters (ANY character in the whitespace
#     CLASS, any mix, any length -- iter3c: matched via the "[[:space:]]" Oniguruma POSIX
#     class rather than an enumerated list, so it is not short by whichever character
#     nobody thought to name; verified own-run to include the full Unicode `White_Space`
#     property -- space/tab/LF/CR/VT/FF/NBSP/ideographic space/U+2028/U+2029/the
#     U+2000-U+200A family -- while zero-width characters U+200B/U+200E correctly remain
#     outside it) OR exactly one ASCII hyphen with no whitespace adjacent to it. $items =
#     scan("[a-z0-9]+|[[:space:]]+|.") turns $text into a flat sequence where every alnum
#     run is one WORD slot, every whitespace run (however long, however mixed across the
#     class) collapses to ONE slot, and every remaining non-alnum/non-whitespace character
#     gets its own one-character slot (so "--" is always two separate one-hyphen slots, and
#     a hyphen next to whitespace, e.g. "trading - order", is a whitespace-slot plus a
#     hyphen-slot -- never one merged slot). phrase_match walks candidate start positions
#     and requires word[j] at slot $start+2*$j and, for every j but the last, a separator at
#     slot $start+2*$j+1; if the gap is a colon, "--", "- " (hyphen+space), or any
#     two-or-more-slot combination, the next real word lands on a slot other than
#     $start+2*(j+1) and the arithmetic simply fails, with no punctuation ever named. This
#     is what makes "trading order" (one space), "trading  order" / "trading   order"
#     (double/triple space, iter3b's fix), "trading\norder" / "trading\torder"
#     (line-wrap/tab, iter3's fix), "trading\rorder" / "trading\r\norder" (bare CR / CRLF,
#     iter3c's fix) and "trading-order" (one hyphen) all match, while "trading: order" /
#     "trading -- order" / "trading - order" (hyphen with whitespace beside it) all
#     correctly do not.
#   - an ASCII when.any item must equal a whole token (or its regular-plural stem, see
#     stem() below), never a fragment
#   - a when.any item containing a space (e.g. "fix protocol") must appear as an
#     ADJACENT run in $items, in that order (iter1 F3 -- the iter0 "AND, not necessarily
#     adjacent" rule reintroduced false positives of the exact shape this bd exists to
#     close, e.g. "in order to speed up trading of assets" wrongly matching "trading
#     order"). Only the phrase's FINAL word accepts the plural-stem relaxation; earlier
#     words must match exactly. This is how the ambiguous single keywords
#     (fix/order/stock/policy/claim/exchange) got disambiguated in routes.json. A
#     single-word item (no space, possibly hyphenated) is matched against $text_tokens
#     instead (single_match()), which keeps a hyphen-joined run as ONE token
#     (scan("[a-z0-9]+(?:-[a-z0-9]+)*") -- iter1 F1: a plain [a-z0-9]+ scan splits
#     "file-upload" into "file"+"upload", so the literal hyphenated string could never
#     appear in the token array and the keyword was permanently dead). Non-capturing
#     group on purpose in both $text_tokens and $items: jq's scan() returns *captured
#     groups* instead of the whole match when the regex has a capturing group, which
#     would silently corrupt the token array into arrays-of-arrays.
#   - stem($x): strips one trailing "s" (length > 4, not a double-s word -- raised from
#     length > 3 in iter2 D2) before comparing, so a phrase's final word (or a standalone
#     single-word keyword) also matches its regular plural -- "trading order" matches
#     "...trading orders...", "insurance claim" matches "...insurance claims..." (iter1
#     F2). The length-3 threshold was too loose: "this refactor saps my energy" wrongly
#     required sap-expert because "saps" (4 chars) stemmed down to "sap" and collided
#     with the unrelated 3-char keyword "sap" -- a real English word, not a plural of
#     SAP the product. Every when.any keyword was checked for the same shape; only the
#     five 3-char-or-shorter keywords ("sap","kyc","mrp","btp","pms") lose plural
#     eligibility for their candidate tokens under the new floor, and none of them had a
#     fixture or requirement relying on it ("mrp"/"mrps" is the one observed loss, judged
#     benign -- same meaning either way -- and accepted rather than special-casing "sap"
#     alone). Every keyword of 4+ chars keeps full plural coverage since its plural form
#     is always 5+ chars and still clears length > 4. Deliberately does NOT handle
#     irregular plurals ("policy"/"policies") -- pre-existing gap, tracked separately,
#     out of scope for this bd. NOT touched by iter3 per the delegation's explicit
#     instruction -- the threshold stays at > 4. Standing policy (Oliver ruling, iter2,
#     see the fuller note above the usage comment's plural-stem paragraph): the
#     mrp/kyc/btp plural loss is accepted permanently; if a plural acronym ever matters,
#     add it as its own explicit `when.any` keyword in routes.json -- never lower this
#     threshold again.
#   - a non-ASCII item (Thai etc.) still uses contains(): Thai script has no ASCII word
#     boundary to tokenize on ([a-z0-9]+ never matches Thai codepoints at all), so
#     forcing token-equality on it would silently stop matching Thai entirely -- that
#     would be a regression, not a fix, per bd:shode-house-5cs.2 instructions. Thai
#     keywords keep the original (unchanged) substring behavior, checked against $text_lc
#     (plain ascii_downcase, no rewriting of any kind since iter3 -- there is no longer a
#     sentinel to not-collide-with).
#   - tags[] matching is untouched: still exact string equality (case-insensitive),
#     never substring
#   - disclosed, non-regressing behavior change (iter3): a bare underscore
#     ("trading_order") no longer bridges two phrase words. Under the old
#     scan()-drops-non-alnum-silently mechanism this happened to still match (never
#     enumerated as intentional, never covered by a fixture -- confirmed absent from both
#     14-oliver-L1-iter1-verified.md and the iter2 review). Underscore is not in the
#     whitespace CLASS and is not the ASCII hyphen, so it is not a separator under either
#     branch of is_separator (iter3c: this stays a two-branch rule, class-or-hyphen, not a
#     literal character set -- see the usage comment's iter3c note above for why) and the
#     new rule does not special-case it in either direction.
jq -n \
  --slurpfile req "$REQ" \
  --slurpfile routesf "$ROUTES" \
  --arg primary "$PRIMARY" \
  --argjson phase_order "$PHASE_ORDER" '
  ($req[0]) as $r
  | ($routesf[0].routes) as $routes
  | (($r.tags // []) | map(ascii_downcase)) as $tags_lc
  | ($r.text // "" | ascii_downcase) as $text_lc
  | ($text_lc | [scan("[a-z0-9]+(?:-[a-z0-9]+)*")]) as $text_tokens
  | ($text_lc | [scan("[a-z0-9]+|[[:space:]]+|.")]) as $items
  | def stem($x):
      if (($x | length) > 4) and ($x | endswith("s")) and (($x | endswith("ss")) | not)
      then $x[0:-1]
      else $x
      end;
  # iter3c: match the whitespace CHARACTER CLASS ("[[:space:]]", Oniguruma POSIX class --
  # verified own-run to include the full Unicode `White_Space` property: space, tab, LF,
  # CR, VT, FF, NBSP, ideographic space, U+2028, U+2029, the U+2000-U+200A family; U+200B
  # and U+200E correctly test false and remain boundaries) instead of the enumerated
  # "[ \t\n]" list iter3b shipped -- that list was short by exactly the characters nobody
  # named (CR chief among them, Chris+Quinn both independently caught it in iter3b
  # re-review), same enumeration-completeness failure this bd has hit every iteration.
  # A class cannot be defeated by a whitespace character nobody thought of.
  def is_separator: (test("^[[:space:]]+$")) or (. == "-");
  def is_word_item: test("^[a-z0-9]+$");
  # single-word ASCII item -- membership check against the hyphen-preserving
  # $text_tokens (unchanged from iter1 F1/iter2 D2; no adjacency involved).
  def single_match($word):
      $text_tokens | any(. as $tok | stem($tok) == stem($word));
  # multi-word ASCII phrase item -- positive adjacency (bd: shode-house-5cs.2 iter3b):
  # word[j] and word[j+1] are adjacent iff EXACTLY ONE item sits between their matching
  # $items slots and that one item is a separator -- a whitespace RUN (any length, since
  # $items already collapses a whitespace run to one slot -- see $items construction
  # below) or a lone ASCII hyphen. Because $items never merges a hyphen with adjacent
  # whitespace into the same slot, a hyphen with whitespace beside it ("trading - order")
  # still occupies two-or-more slots in the gap, same as a colon, an em-dash typed as
  # "--", or any future punctuation nobody has enumerated yet -- which pushes the next
  # word two-or-more slots further than the fixed $start+2*$j arithmetic expects, so the
  # index check fails and adjacency breaks by construction. No punctuation is named
  # anywhere in this rule; only the two allowed separator shapes are (is_separator).
  def phrase_match($words):
      ($items | length) as $ilen
      | ($words | length) as $n
      | ((2 * $n) - 1) as $span
      | ($ilen - $span) as $maxstart
      | if $maxstart < 0 then false
        else
          [range(0; $maxstart + 1)]
          | any(. as $start
              | (
                  [range(0; $n)]
                  | all(. as $j
                      | ($items[$start + (2 * $j)]) as $tok
                      | ($tok | is_word_item)
                        and (if $j == ($n - 1)
                             then (stem($tok) == stem($words[$j]))
                             else ($tok == $words[$j])
                             end)
                    )
                )
                and (
                  [range(0; $n - 1)]
                  | all(. as $j
                      | ($items[$start + (2 * $j) + 1]) as $sep
                      | ($sep | is_separator)
                    )
                )
              )
        end;
  def word_match($item_lc):
      if ($item_lc | test("^[\\x00-\\x7f]*$")) then
        ($item_lc | split(" ")) as $words
        | if ($words | length) > 1
          then phrase_match($words)
          else single_match($words[0])
          end
      else
        ($text_lc | contains($item_lc))
      end;
  (
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
                                 | ($item | ascii_downcase) as $item_lc
                                 | ($tags_lc | index($item_lc)) != null
                                   or word_match($item_lc)))
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
