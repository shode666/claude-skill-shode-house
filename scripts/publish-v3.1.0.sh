#!/usr/bin/env bash
# DEPRECATED — use scripts/publish.sh instead (version-agnostic)
exec "$(dirname "$0")/publish.sh" "$@"
