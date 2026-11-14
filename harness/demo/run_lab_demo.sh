#!/usr/bin/env bash
# harness/demo/run_lab_demo.sh
# Lab demonstration runner for fresh-memory visitor evaluation scenarios.
# Starts Gatekeeper with an isolated SQLite DB per scenario, starts Cowrie sensor,
# executes attacker scenario on loopback, and prints recorded decision rows.
# Refuses any non-loopback host.

set -e

HOST="127.0.0.1"
PORT=2222
GK_PORT=5000
DRY_RUN=0

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --gatekeeper-port)
            GK_PORT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--host 127.0.0.1] [--port 2222] [--gatekeeper-port 5000]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# Strict loopback safety assertion
if [ "$HOST" != "127.0.0.1" ] && [ "$HOST" != "localhost" ]; then
    echo "SAFETY ERROR: Refusing non-loopback host '$HOST'. Only 127.0.0.1 or localhost is permitted." >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    PYTHON="python"
fi

SCENARIOS=("bot_like" "interactive" "transfer_like")

if [ "$DRY_RUN" -eq 1 ]; then
    echo "[DRY-RUN] Validated target host: $HOST:$PORT (loopback authorized)"
    echo "[DRY-RUN] Python interpreter: $PYTHON"
    for scenario in "${SCENARIOS[@]}"; do
        echo "[DRY-RUN] --- Scenario: $scenario ---"
        echo "[DRY-RUN] 1. Would create temp DB: mktemp /tmp/gk_demo_XXXXXX.db"
        echo "[DRY-RUN] 2. Would start Gatekeeper: $PYTHON -m gatekeeper.decision_api --host 127.0.0.1 --port $GK_PORT --db <db_path>"
        echo "[DRY-RUN] 3. Would start Sensor: $PYTHON -m sensor.run_sensor --state-dir <cowrie_state> --port $PORT --gatekeeper-url http://127.0.0.1:$GK_PORT"
        echo "[DRY-RUN] 4. Would execute attacker: $PYTHON -m harness.attackers.$scenario --host $HOST --port $PORT"
        echo "[DRY-RUN] 5. Would print schema and decision log rows from SQLite database"
        echo "[DRY-RUN] 6. Would terminate sensor and gatekeeper background processes and cleanup temporary files"
    done
    exit 0
fi

# Live execution loop across scenarios
for scenario in "${SCENARIOS[@]}"; do
    echo "================================================================="
    echo "Starting isolated fresh-memory demo run for scenario: $scenario"
    echo "================================================================="

    DB_PATH="$(mktemp /tmp/gk_demo_XXXXXX.db)"
    COWRIE_STATE="$(mktemp -d /tmp/cowrie_state_XXXXXX)"
    ASKPASS="$(mktemp /tmp/askpass_XXXXXX)"

    printf '#!/bin/sh\nprintf "%%s\\n" root\n' > "$ASKPASS"
    chmod 700 "$ASKPASS"

    GK_PID=""
    SENSOR_PID=""

    cleanup() {
        if [ -n "$SENSOR_PID" ]; then
            kill "$SENSOR_PID" 2>/dev/null || true
            wait "$SENSOR_PID" 2>/dev/null || true
        fi
        if [ -n "$GK_PID" ]; then
            kill "$GK_PID" 2>/dev/null || true
            wait "$GK_PID" 2>/dev/null || true
        fi
        rm -f "$ASKPASS" "$DB_PATH"
        rm -rf "$COWRIE_STATE"
    }

    # Start Gatekeeper
    "$PYTHON" -m gatekeeper.decision_api --host 127.0.0.1 --port "$GK_PORT" --db "$DB_PATH" > /dev/null 2>&1 &
    GK_PID=$!

    # Wait for Gatekeeper to be responsive
    for _ in $(seq 1 50); do
        if nc -z 127.0.0.1 "$GK_PORT" 2>/dev/null || (echo > /dev/tcp/127.0.0.1/"$GK_PORT") 2>/dev/null; then
            break
        fi
        sleep 0.1
    done

    # Start Sensor
    "$PYTHON" -m sensor.run_sensor --state-dir "$COWRIE_STATE" --port "$PORT" --gatekeeper-url "http://127.0.0.1:$GK_PORT" > /dev/null 2>&1 &
    SENSOR_PID=$!

    # Wait for Sensor port
    for _ in $(seq 1 100); do
        if nc -z 127.0.0.1 "$PORT" 2>/dev/null || (echo > /dev/tcp/127.0.0.1/"$PORT") 2>/dev/null; then
            break
        fi
        sleep 0.1
    done

    # Run attacker scenario with temporary askpass
    export SSH_ASKPASS="$ASKPASS"
    export SSH_ASKPASS_REQUIRE="force"
    export DISPLAY=":lab"

    "$PYTHON" -m "harness.attackers.$scenario" --host "$HOST" --port "$PORT" || true

    sleep 1

    # Terminate sensor and gatekeeper
    kill "$SENSOR_PID" 2>/dev/null || true
    wait "$SENSOR_PID" 2>/dev/null || true
    SENSOR_PID=""

    kill "$GK_PID" 2>/dev/null || true
    wait "$GK_PID" 2>/dev/null || true
    GK_PID=""

    # Inspect SQLite Schema and print Decision Rows
    echo ""
    echo "--- Decision Log Schema for $scenario ---"
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$DB_PATH" ".schema decision_log"
    else
        "$PYTHON" -c "import sqlite3; conn=sqlite3.connect('$DB_PATH'); row=conn.execute(\"SELECT sql FROM sqlite_master WHERE type='table' AND name='decision_log'\").fetchone(); print(row[0] if row else 'Table not found')"
    fi

    echo ""
    echo "--- Recorded Decision Rows for $scenario ---"
    "$PYTHON" -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
rows = conn.execute('SELECT session_id, stage, tier_decided, score FROM decision_log ORDER BY id').fetchall()
if not rows:
    print('NO DECISIONS RECORDED')
for sid, stage, tier, score in rows:
    masked_sid = sid[:8] + '...' if len(sid) > 8 else sid
    print(f'session_id: {masked_sid} | stage: {stage} | tier_decided: {tier} | score: {score:.4f} | threshold: TODO(verify): column not stored in decision_log')
"
    echo ""

    cleanup
done

echo "Lab demo scenarios completed."
