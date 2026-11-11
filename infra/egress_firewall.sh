#!/usr/bin/env bash
# ============================================================================
# egress_firewall.sh: Honeypot Network Isolation & Egress Filtering Script
# Mandated by SAFETY.md Rule 2.2 and Rule 6: "Outbound egress strictly forbidden"
# ============================================================================

set -euo pipefail

echo "[*] Initializing Schrödinger's Server Honeypot Egress Firewall..."

# Flush existing rules on honeypot chain if exists
iptables -F OUTPUT || true
iptables -F FORWARD || true

# Set default policies to DROP (Fail-secure containment)
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# 1. Allow local loopback traffic (Crucial for Gatekeeper <-> Sensor <-> Router IPC)
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# 2. Allow established/related incoming sessions (Responding to inbound attacker commands)
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# 3. Log and DROP all other outbound connection attempts (No botnet C2 pivots or DDoS participation)
iptables -A OUTPUT -m limit --limit 5/min -j LOG --log-prefix "[HONEYPOT-EGRESS-BLOCKED]: " --log-level 4
iptables -A OUTPUT -j DROP

echo "[+] Egress firewall active: All outbound internet packets from honeypot are dropped."
