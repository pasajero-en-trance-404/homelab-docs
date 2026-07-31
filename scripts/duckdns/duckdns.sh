#!/usr/bin/env bash
set -euo pipefail

CONF="$HOME/homelab-data/duckdns/duckdns.conf"
LOG="$HOME/homelab-data/duckdns/duckdns.log"

if [[ ! -f "$CONF" ]]; then
    echo "[$(date -Iseconds)] ERROR: config not found at $CONF" | tee -a "$LOG"
    exit 1
fi

source "$CONF"

if [[ -z "${DUCKDNS_DOMAIN:-}" || -z "${DUCKDNS_TOKEN:-}" ]]; then
    echo "[$(date -Iseconds)] ERROR: DUCKDNS_DOMAIN or DUCKDNS_TOKEN not set in $CONF" | tee -a "$LOG"
    exit 1
fi

CURRENT_IP=$(curl -s -4 https://checkip.amazonaws.com 2>/dev/null || curl -s -4 https://api.ipify.org 2>/dev/null || echo "")

if [[ -z "$CURRENT_IP" ]]; then
    echo "[$(date -Iseconds)] ERROR: could not detect public IP" | tee -a "$LOG"
    exit 1
fi

URL="https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=${CURRENT_IP}"
RESPONSE=$(curl -s "$URL")

echo "[$(date -Iseconds)] domain=${DUCKDNS_DOMAIN} ip=${CURRENT_IP} response=${RESPONSE}" | tee -a "$LOG"
