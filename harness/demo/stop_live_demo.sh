#!/usr/bin/env bash
# Match process start times to avoid signaling a recycled PID.
set -eu
if [[ ${1:-} == --dry-run ]]; then echo 'Stop recorded demo processes'; exit; fi
dir=${1:?Pass DEMO_DIR printed by start_live_demo.sh}
for name in dashboard sensor gatekeeper; do
    file="$dir/$name.pid"
    [[ -f $file ]] || continue
    read -r pid start <"$file"
    [[ $pid =~ ^[1-9][0-9]+$ && $start =~ ^[0-9]+$ ]] || exit 1
    if [[ $(awk '{print $22}' "/proc/$pid/stat" 2>/dev/null || :) == "$start" ]]; then
        kill -TERM "$pid"
    fi
done
