#!/bin/bash

# Restore DOCKER-USER firewall rules after boot.
# Waits for Docker to create the DOCKER-USER chain, then applies rules.
# Idempotent: safe to run multiple times.
# Protected against concurrent execution via flock.

set -u

# ── Lock (prevent concurrent execution) ────────────────
LOCKFILE=/run/restore-docker-user.lock
exec 200>"$LOCKFILE"
flock -n 200 || {
    echo "ERROR [restore-docker-user]: Another instance is running (lock held: $LOCKFILE)" >&2
    logger -t restore-docker-user "ERROR: Another instance is running (lock held)"
    exit 1
}

# ── Wait for Docker DOCKER-USER chain ──────────────────
TIMEOUT=30
INTERVAL=2
elapsed=0

while [ "$elapsed" -lt "$TIMEOUT" ]; do
    if iptables -L DOCKER-USER -n >/dev/null 2>&1; then
        break
    fi
    sleep "$INTERVAL"
    elapsed=$((elapsed + INTERVAL))
done

# Final check
if ! iptables -L DOCKER-USER -n >/dev/null 2>&1; then
    echo "ERROR [restore-docker-user]: DOCKER-USER chain not found after ${TIMEOUT}s." >&2
    echo "Is Docker running? Check: systemctl status docker" >&2
    logger -t restore-docker-user "ERROR: DOCKER-USER chain not found after ${TIMEOUT}s"
    exit 1
fi

set -e

# ── Flush existing rules (chain confirmed exists) ──────
iptables -F DOCKER-USER

# ── Apply rules ────────────────────────────────────────
# 1. Established/related connections (keep active sessions)
iptables -A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# 2. All traffic from Tailscale
iptables -A DOCKER-USER -i tailscale0 -j ACCEPT

# 3. Container outbound: DNS (UDP + TCP)
iptables -A DOCKER-USER -i br+ -p udp --dport 53 -j ACCEPT
iptables -A DOCKER-USER -i br+ -p tcp --dport 53 -j ACCEPT
iptables -A DOCKER-USER -i docker0 -p udp --dport 53 -j ACCEPT
iptables -A DOCKER-USER -i docker0 -p tcp --dport 53 -j ACCEPT

# 4. Container outbound: HTTP/HTTPS
iptables -A DOCKER-USER -i br+ -p tcp -m multiport --dports 80,443 -j ACCEPT
iptables -A DOCKER-USER -i docker0 -p tcp -m multiport --dports 80,443 -j ACCEPT

# 5. Container outbound: ICMP ping
iptables -A DOCKER-USER -i br+ -p icmp --icmp-type echo-request -j ACCEPT
iptables -A DOCKER-USER -i br+ -p icmp --icmp-type echo-reply -j ACCEPT
iptables -A DOCKER-USER -i docker0 -p icmp --icmp-type echo-request -j ACCEPT
iptables -A DOCKER-USER -i docker0 -p icmp --icmp-type echo-reply -j ACCEPT

# 6. LAN access: only Homepage dashboard
iptables -A DOCKER-USER -s 192.168.1.0/24 -p tcp --dport 3000 -j ACCEPT

# 7. Block everything else
iptables -A DOCKER-USER -j DROP

logger -t restore-docker-user "DOCKER-USER rules applied successfully"
echo "restore-docker-user: DOCKER-USER rules applied successfully"
