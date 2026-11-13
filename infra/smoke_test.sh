#!/usr/bin/env bash
# ==============================================================================
# Docker Compose Smoke Test for Schrödinger's Server Infrastructure
# Enforces G8:
# 1. Validates docker-compose.yml syntax via docker compose config.
# 2. Prints published ports and host addresses.
# 3. Asserts no service publishes on 0.0.0.0 unless explicitly allowlisted.
# 4. Asserts internal_honeypot_net is declared internal: true.
# 5. Starts containers ONLY if --up is passed.
# ==============================================================================

set -euo pipefail

# Allowlist for 0.0.0.0 published ports (default: empty / none)
WHITELISTED_0000_PORTS=()

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
PARSER_SCRIPT="${SCRIPT_DIR}/parse_compose.py"

DO_UP=false
for arg in "$@"; do
    if [ "$arg" == "--up" ]; then
        DO_UP=true
    fi
done

echo "=========================================================="
echo "Schrödinger's Server // Infrastructure Smoke Test (G8)"
echo "Compose File: ${COMPOSE_FILE}"
echo "=========================================================="

if [ ! -f "${COMPOSE_FILE}" ]; then
    echo "[ERROR] Compose file not found: ${COMPOSE_FILE}" >&2
    exit 1
fi

# 1. Run docker compose config if docker is available
if command -v docker &>/dev/null; then
    echo "[1/4] Validating compose configuration via 'docker compose config'..."
    docker compose -f "${COMPOSE_FILE}" config > /dev/null
    echo "  [OK] docker compose config syntax valid."
else
    echo "[1/4] Docker CLI not found in PATH; performing static validation..."
fi

# 2 & 3. Parse published ports and verify host addresses using parse_compose.py
echo ""
echo "[2/4] Inspecting published ports and host interface bindings..."

INTERNAL_NET=false

while IFS= read -r line; do
    if [[ "$line" =~ ^PORT:([^:]+):(.+)$ ]]; then
        SERVICE="${BASH_REMATCH[1]}"
        BINDING="${BASH_REMATCH[2]}"
        echo "  -> Service '${SERVICE}' publishes: ${BINDING}"
        # Check 0.0.0.0 violations
        if [[ "$BINDING" =~ ^0\.0\.0\.0: ]] || [[ ! "$BINDING" =~ ^127\.0\.0\.1: ]]; then
            IS_WHITELISTED=false
            for w in "${WHITELISTED_0000_PORTS[@]-}"; do
                if [ "$w" == "$BINDING" ]; then
                    IS_WHITELISTED=true
                    break
                fi
            done
            if [ "$IS_WHITELISTED" = false ]; then
                echo "[ERROR] Security Violation: Service '${SERVICE}' publishes on 0.0.0.0 without allowlist: ${BINDING}" >&2
                exit 1
            fi
        fi
    elif [ "$line" == "INTERNAL_NETWORK:True" ]; then
        INTERNAL_NET=true
    fi
done < <(python3 "${PARSER_SCRIPT}" "${COMPOSE_FILE}")

echo ""
echo "[3/4] Verifying interface security (0.0.0.0 rejection)..."
echo "  [OK] Zero unauthorized 0.0.0.0 port publications. All ports bound to 127.0.0.1."

echo ""
echo "[4/4] Verifying network isolation declaration..."
if [ "$INTERNAL_NET" != true ]; then
    echo "[ERROR] internal_honeypot_net is NOT declared with 'internal: true'!" >&2
    exit 1
fi
echo "  [OK] Lab network 'internal_honeypot_net' declared with 'internal: true'."

if [ "$DO_UP" = true ]; then
    echo ""
    echo "[UP] Starting services via docker compose up -d..."
    docker compose -f "${COMPOSE_FILE}" up -d
else
    echo ""
    echo "[NOTICE] Containers NOT started (--up was not passed). Smoke test completed."
fi

echo ""
echo "SMOKE TEST PASSED."
exit 0
