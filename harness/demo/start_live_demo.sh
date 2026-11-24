#!/usr/bin/env bash
# Start the native loopback lab and print its private state directory.
set -euo pipefail
cd "$(dirname "$0")/../.."
scenes() {
    echo 'LAB_DEMO_NOT_ML http://127.0.0.1:8080'
    echo 'python -m harness.attackers.bot_like --host 127.0.0.1 --port 12222 --username root --source-ip 127.0.0.2'
    echo 'python -m harness.attackers.interactive --host 127.0.0.1 --port 12222 --username root --source-ip 127.0.0.3'
    echo 'python -m harness.attackers.slow_recon --host 127.0.0.1 --port 12222 --source-ip 127.0.0.4'
    echo 'python -m harness.attackers.interactive --host 127.0.0.1 --port 12222 --username root --source-ip 127.0.0.3'
}
if [[ ${1:-} == --dry-run ]]; then scenes; exit; fi
if (($#)); then exit 2; fi
available() { [[ -z "$(ss -H -ltn "sport = :$1")" ]]; }
command -v ss >/dev/null
for port in 15000 12222 8080; do
    available "$port" || { echo "Port $port occupied"; exit 1; }
done
umask 077
dir=$(mktemp -d)
echo "DEMO_DIR=$dir"
trap 'bash harness/demo/stop_live_demo.sh "$dir"' EXIT
trap 'exit 130' INT TERM
launch() {
    local name=$1 port=$2 pid
    shift 2
    nohup python -m "$@" >"$dir/$name.log" 2>&1 </dev/null &
    pid=$!
    echo "$pid $(awk '{print $22}' "/proc/$pid/stat")" >"$dir/$name.pid"
    for ((i=0;i<120;i++)); do
        kill -0 "$pid" 2>/dev/null || break
        if ss -Hltnp "sport = :$port" | grep -Fq "pid=$pid,"; then return; fi
        sleep .25
    done
    echo "$name failed to listen; see $dir/$name.log" >&2
    return 1
}
launch gatekeeper 15000 gatekeeper.decision_api --host 127.0.0.1 --port 15000 --lab-mode --db "$dir/live.db"
launch sensor 12222 sensor.run_sensor --state-dir "$dir/sensor" --gatekeeper-url http://127.0.0.1:15000 --port 12222
launch dashboard 8080 dashboard.app --host 127.0.0.1 --port 8080 --db "$dir/live.db" --mode LAB
trap - EXIT INT TERM
scenes
printf 'Stop: bash harness/demo/stop_live_demo.sh %q\n' "$dir"
