#!/usr/bin/env bash
# Spike: PreToolUse deny probe. Blocks direct writes into .shode-house/state/.
# Exit 2 = the ONLY exit code that blocks (exit 1 is non-blocking — docs).
set -u
input=$(cat)
case "$input" in
  *'.shode-house/state/'*)
    echo "shode-house: direct write to .shode-house/state/ is denied — use the transition validator" >&2
    exit 2
    ;;
esac
exit 0
