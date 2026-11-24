#!/usr/bin/env bash
# Verify the native scripts without opening sockets.
set -euo pipefail
cd "$(dirname "$0")/../.."
for script in harness/demo/{start,stop}_live_demo.sh; do
    bash -n "$script"
    bash "$script" --dry-run >/dev/null
done
output=$(bash harness/demo/start_live_demo.sh --dry-run)
[[ $(grep -c '^python -m harness.attackers' <<<"$output") == 4 ]]
if grep -Eo '([0-9]+\.){3}[0-9]+' <<<"$output" | grep -qv '^127\.'; then exit 1; fi
