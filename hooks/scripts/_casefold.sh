#!/usr/bin/env bash
# _casefold.sh -- the ONE case fold behind every protected-path comparison
# (bd: shode-house-v7u.4.34; Chris W8 r3 S2, router R74 NF1/NF2 and R77, Sentinel W8 r3
# FU-R3a and pre-release B2).
#
# Sourced, never executed (mode 644, like _lib.sh). Callers:
#   hooks/scripts/guard-scope-write.sh  -- ux path set, scope-manifest check, .git check (deny side);
#                                          project-root strip
#   hooks/scripts/guard-state-write.sh  -- .shode-house/{state,journal}                  (deny side)
#   scripts/scope-check.sh              -- path_matches (owner grant) and path_matches_deny
#                                          (outsider collision, plus _scope_nfc_batch_deny
#                                          on macOS); project-root strip
# The shebang is here only so shellcheck can lint this file on its own.
#
# Two entry points (router R77):
#
# _scope_fold <s> -- the DETERMINISTIC fold. Sets the global _scope_folded (no subshell,
#   no process at all unless <s> holds an ASCII upper-case letter). Same result on every
#   platform and in every caller locale:
#   1. Code points that APFS treats as ASCII letters are mapped to them (UTF-8 bytes):
#        U+017F long s -> s          U+212A Kelvin sign -> k
#        U+FB00 ff  U+FB01 fi  U+FB02 fl  U+FB03 ffi  U+FB04 ffl  U+FB05 st  U+FB06 st
#        U+00DF sharp s -> ss        U+1E9E capital sharp s -> ss
#      A scan of every code point on APFS found these eleven that fold to ASCII letters.
#      The expansions matter: "state", "tsconfig" and "*.config.json" contain "st" and
#      "fi", so "ﬆate" and "tsconﬁg.json" ARE "state" and "tsconfig.json" on disk
#      (Sentinel pre-release B2, measured). Re-check this list when a protected word is
#      added or when the platform folds more code points.
#   2. ASCII A-Z -> a-z (`tr` runs only when an upper-case ASCII letter is present).
#   scope-check.sh's path_matches uses only this fold: it decides owner matches, so a
#   platform-dependent widening there could grant a write (router R77).
#
# _scope_casefold <s> -- prints _scope_fold's result (the same deterministic fold, for
#   callers that want stdout).
#
# _scope_fold_deny <s> (sets _scope_folded) and _scope_casefold_deny <s> (prints it) --
#   DENY SIDE ONLY. The deterministic fold, then, only when non-ASCII bytes remain, the
#   platform's own Unicode lower-casing:
#   `tr '[:upper:]' '[:lower:]'` under a UTF-8 locale (C.UTF-8, then en_US.UTF-8), kept
#   only when tr exits 0 (on an invalid byte a UTF-8 tr stops and exits 1; that output is
#   discarded, so the fold never truncates). macOS tr lowers U+00DC to U+00FC there, and
#   APFS treats both as one name. Where tr is byte-based (GNU) or no UTF-8 locale exists,
#   this step changes nothing. Used only where a wider fold can only ADD denies (both
#   guards); never for a grant (router R77). scope-check.sh uses it for the checks that
#   DENY an outsider (router R78: --main-check and a collision with another agent's
#   pattern), never for an owner match.
#
# _scope_nfc_batch_deny <candidate> -- DENY SIDE ONLY, macOS only (UD U12, Sentinel
#   pre-release r3 F-6), and ONE normaliser process per check (UD U20, Sentinel r7 F7-1,
#   Chris r7 F1). A filter: stdin holds the manifest strings of one check, one per line,
#   each tagged "K<shared_files key>" or "T<agent><TAB><pattern>" (the pattern is the part
#   after the first TAB). stdout gets NUL-terminated records: "C<NFC of candidate>", then for
#   every distinct NON-ASCII string "R<raw>" and "N<its NFC>", sorted by the raw bytes (the
#   order of [[ < ]] under LC_ALL=C), then "E". No "E" means failure: <candidate> could not be
#   normalised (not valid UTF-8, or /usr/bin/perl missing or failing), and the caller must
#   DENY with a clear message, never fall back to the unnormalised spelling. A string perl
#   cannot decode gets no record; the caller counts it as a collision. A line that holds a NUL
#   byte (a JSON "\u0000" in a manifest string, which jq -r writes raw) gets no record either:
#   inside a NUL-terminated record it would split into forged records (Sentinel U20 F8-1,
#   Chris U20 N-1). APFS treats canonically
#   equivalent spellings as one name (NFC and NFD of an accented name, Thai marks typed in
#   another order, singletons such as U+0958), so a collision check that compares spellings
#   misses them. For an ASCII-only <candidate>, or off macOS (_scope_is_macos), it prints
#   "C<candidate>" and "E", reads nothing and starts no process: Linux file systems keep NFC
#   and NFD apart, so nothing is normalised there. Only scope-check.sh's outsider collision
#   (path_matches_deny, router R78) uses it; never a grant, never the guards' own protected
#   names (ASCII words, or matched by directory identity).
#   Normaliser: /usr/bin/perl with Unicode::Normalize, part of the macOS base system, by
#   absolute path, in one process for the candidate and every pattern. -T ignores PERL5LIB
#   and PERL5OPT, -C0 ignores PERL_UNICODE, binmode drops any I/O layer, and the candidate is
#   argv after "--" (data, never code). Measured on macOS 27 (APFS): it gives Unicode's NFC
#   for all 13,233 code points with a canonical decomposition, and every pair APFS treats as
#   one name gets one key. /usr/bin/iconv (UTF-8-MAC) was rejected: 605 such pairs got
#   different keys and it failed on 575.
#
# _scope_strip_root <abs> <root> -- the project-root prefix strip shared by the scope guard
#   and scope-check.sh (router R78, Sentinel pre-release r2 F-1); see the function.
#
# Byte semantics. Every entry point folds under LC_ALL=C, and every caller also matches under
# LC_ALL=C. In a multibyte locale such as ja_JP.SJIS the UTF-8 bytes of a character like
# U+3042 end in a byte that SJIS reads as a lead byte, so bash's pattern matching
# swallows the next ASCII letter and "design-run-order" after it is not seen (measured:
# rc 0 under SJIS, rc 2 under C). Under C both steps work on bytes, the same bytes the
# kernel compares.
#
# The output is for comparison only. Callers never show it to a user and never write it
# anywhere, so the real-cased path stays in messages and audit lines.
_scope_fold() {
  local LC_ALL=C
  _scope_folded=$1
  case "$_scope_folded" in
    *[$'\x80'-$'\xff']*)
      _scope_folded=${_scope_folded//$'\xc5\xbf'/s}
      _scope_folded=${_scope_folded//$'\xe2\x84\xaa'/k}
      _scope_folded=${_scope_folded//$'\xef\xac\x80'/ff}
      _scope_folded=${_scope_folded//$'\xef\xac\x81'/fi}
      _scope_folded=${_scope_folded//$'\xef\xac\x82'/fl}
      _scope_folded=${_scope_folded//$'\xef\xac\x83'/ffi}
      _scope_folded=${_scope_folded//$'\xef\xac\x84'/ffl}
      _scope_folded=${_scope_folded//$'\xef\xac\x85'/st}
      _scope_folded=${_scope_folded//$'\xef\xac\x86'/st}
      _scope_folded=${_scope_folded//$'\xc3\x9f'/ss}
      _scope_folded=${_scope_folded//$'\xe1\xba\x9e'/ss}
      ;;
  esac
  case "$_scope_folded" in
    *[ABCDEFGHIJKLMNOPQRSTUVWXYZ]*)
      # The trailing "x" keeps a trailing newline in the name; $(...) would strip it.
      _scope_folded=$(printf '%s' "$_scope_folded" | tr 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' 'abcdefghijklmnopqrstuvwxyz'; printf x)
      _scope_folded=${_scope_folded%x}
      ;;
  esac
}

_scope_casefold() {
  _scope_fold "$1"
  printf '%s' "$_scope_folded"
}

_scope_fold_deny() {
  local LC_ALL=C u loc
  _scope_fold "$1"
  case "$_scope_folded" in
    *[$'\x80'-$'\xff']*)
      for loc in C.UTF-8 en_US.UTF-8; do
        u=$(printf '%s' "$_scope_folded" | LC_ALL="$loc" tr '[:upper:]' '[:lower:]' 2>/dev/null && printf x) && _scope_folded="${u%x}"
      done ;;
  esac
}

_scope_casefold_deny() {
  _scope_fold_deny "$1"
  printf '%s' "$_scope_folded"
}

# _scope_is_macos -- returns 0 on macOS, the one platform whose file system makes the NFC
# compare necessary, and 1 elsewhere (Sentinel r7 F7-4). The signal is the kernel's own name,
# from uname by absolute path (/usr/bin/uname, or /bin/uname where coreutils keeps it), run
# with an EMPTY environment (exec -c): macOS's uname prints UNAME_s or UNAME_SYSNAME from its
# environment in place of the kernel's name (Sentinel U21 F7-4-R), and $OSTYPE is never read,
# so no variable of the hook's environment can set the answer. A platform that cannot be
# determined (no uname at either path, or no output) counts as macOS: the NFC compare then
# runs, and a path it cannot normalise is denied (fail closed; it can only add denies). The
# answer is kept in _scope_os for the rest of the process; it is reset when this file is
# sourced, so a value from the environment is never used. It starts a process only the first
# time it is called, and only for a non-ASCII path (the callers test that first).
_scope_os=""
_scope_is_macos() {
  local u=""
  if [ -z "$_scope_os" ]; then
    if [ -x /usr/bin/uname ]; then u=$(exec -c /usr/bin/uname -s 2>/dev/null)
    elif [ -x /bin/uname ]; then u=$(exec -c /bin/uname -s 2>/dev/null)
    fi
    _scope_os=${u:-unknown}
  fi
  case "$_scope_os" in Darwin|unknown) return 0 ;; esac
  return 1
}

_scope_nfc_batch_deny() {
  local LC_ALL=C
  case "$1" in *[$'\x80'-$'\xff']*) : ;; *) printf 'C%s\0E\0' "$1"; return 0 ;; esac
  _scope_is_macos || { printf 'C%s\0E\0' "$1"; return 0; }
  /usr/bin/perl -T -C0 -MUnicode::Normalize -e '
    binmode STDIN; binmode STDOUT;
    my $c = shift; utf8::decode($c) or exit 3; $c = NFC($c); utf8::encode($c);
    my %raw;
    while (my $l = <STDIN>) {
      chomp $l;
      next if index($l, "\0") >= 0;
      my $tag = substr($l, 0, 1, "");
      if ($tag eq "T") { my $i = index($l, "\t"); next if $i < 0; $l = substr($l, $i + 1) }
      elsif ($tag ne "K") { next }
      $raw{$l} = 1 if $l =~ /[\x80-\xff]/;
    }
    print "C", $c, "\0";
    for my $r (sort keys %raw) {
      my $d = $r; utf8::decode($d) or next; $d = NFC($d); utf8::encode($d);
      print "R", $r, "\0N", $d, "\0";
    }
    print "E\0"' -- "$1" 2>/dev/null
}

# _scope_strip_root <abs> <root> -- sets the global _scope_rel to <abs> relative to the
# project root <root> ("." for the root itself) and returns 0, or leaves <abs> unchanged in
# _scope_rel and returns 1 when <abs> is not under <root>. Router R78 / Sentinel pre-release
# r2 F-1: `pwd -P` keeps the spelling it was given, so ".../SHK2/p/src/x.ts" on a
# case-insensitive volume is under a root spelled ".../shk2/p", and a byte-exact prefix
# test left it absolute, outside every manifest rule. The fast path is that byte-exact
# test. Otherwise the prefix of <abs> with as many components as <root> (every fold keeps
# "/" where it is, so this is "strip by length") is stripped when it is the SAME directory
# as <root> (`-ef`, device and inode): that covers every spelling the filesystem itself
# treats as one name (case, the folds above, Unicode normalisation) and never strips a
# different directory on a case-sensitive volume, where the folded spellings differ on disk.
_scope_strip_root() {
  local LC_ALL=C p="$1" r="$2" n rs pre="" rest seg
  _scope_rel=$p
  case "$p" in
    "$r")   _scope_rel=.; return 0 ;;
    "$r"/*) _scope_rel=${p#"$r"/}; return 0 ;;
  esac
  case "$r" in /?*) : ;; *) return 1 ;; esac
  case "$p" in /?*) : ;; *) return 1 ;; esac
  rs=${r//[!\/]/}; n=${#rs}
  rest=${p#/}
  while [ "$n" -gt 0 ]; do
    [ -n "$rest" ] || return 1
    seg=${rest%%/*}
    pre="$pre/$seg"
    case "$rest" in */*) rest=${rest#*/} ;; *) rest="" ;; esac
    n=$((n - 1))
  done
  [ "$pre" -ef "$r" ] || return 1
  if [ -n "$rest" ]; then _scope_rel=$rest; else _scope_rel=.; fi
  return 0
}
