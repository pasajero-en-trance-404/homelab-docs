#!/usr/bin/env bash
# Homelab bootstrap v1.1
# Idempotent bootstrap: rebuilds the whole homelab from a fresh Debian 13 install.
#
# Usage:
#   sudo ./bootstrap/bootstrap.sh
#
# Config: reads vars.env from the same directory if present (see vars.env.example).
# Run it on a freshly installed Debian 13 with a working internet connection.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Load configuration ──────────────────────────────────────────────
if [[ -f "$SCRIPT_DIR/vars.env" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/vars.env"
else
    echo "WARN: $SCRIPT_DIR/vars.env not found, using defaults."
fi

TARGET_USER="${TARGET_USER:-administrador}"
TARGET_HOME="${TARGET_HOME:-/home/administrador}"
DATA_ROOT="${DATA_ROOT:-$TARGET_HOME/homelab-data}"
HOMELAB_NETWORK="${HOMELAB_NETWORK:-homelab}"
HOMELAB_SUBNET="${HOMELAB_SUBNET:-172.22.0.0/16}"
LAN_SUBNET="${LAN_SUBNET:-192.168.1.0/24}"
TS_AUTH_KEY="${TS_AUTH_KEY:-}"
TS_HOSTNAME="${TS_HOSTNAME:-debian-server}"
TS_FUNNEL="${TS_FUNNEL:-true}"
API_PORT="${API_PORT:-8000}"
GPG_RECIPIENT="${GPG_RECIPIENT:-}"

log() { echo "[bootstrap][$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { log "ERROR: $*"; exit 1; }

# ── Preflight ───────────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || die "Run as root: sudo ./bootstrap/bootstrap.sh"

command -v curl >/dev/null 2>&1 || die "curl is required (apt install curl)"

if ! grep -q '^ID=debian$' /etc/os-release; then
    die "This bootstrap targets Debian only."
fi

log "=== Homelab bootstrap v1.1 ==="
log "Target user : $TARGET_USER"
log "Data root   : $DATA_ROOT"
log "Repo dir    : $REPO_DIR"

# ── Helpers ─────────────────────────────────────────────────────────
apt_install() {
    DEBIAN_FRONTEND=noninteractive apt-get install -y "$@" >/dev/null
}

is_installed() { dpkg -s "$1" >/dev/null 2>&1; }

run_as_user() {
    if [[ "$(id -un)" == "$TARGET_USER" ]]; then
        "$@"
    else
        sudo -u "$TARGET_USER" -- "$@"
    fi
}

# ── 1. Base packages ────────────────────────────────────────────────
base_packages() {
    log "[1/9] Installing base packages..."
    apt-get update >/dev/null
    for pkg in ca-certificates curl git gnupg software-properties-common iptables openssl; do
        is_installed "$pkg" || apt_install "$pkg"
    done
    log "[1/9] Base packages OK"
}

# ── 2. Docker Engine + Compose plugin ───────────────────────────────
install_docker() {
    log "[2/9] Installing Docker Engine + Compose plugin..."

    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        log "[2/9] Docker already installed: $(docker --version), compose $(docker compose version --short)"
        return
    fi

    apt_install ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list

    apt-get update >/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null

    systemctl enable --now docker
    usermod -aG docker "$TARGET_USER"

    log "[2/9] Docker installed: $(docker --version), compose $(docker compose version --short)"
}

# ── 3. Tailscale ────────────────────────────────────────────────────
install_tailscale() {
    log "[3/9] Installing Tailscale..."

    if command -v tailscale >/dev/null 2>&1; then
        log "[3/9] Tailscale already installed."
    else
        curl -fsSL https://tailscale.com/install.sh | sh
    fi

    if tailscale status >/dev/null 2>&1; then
        log "[3/9] Tailscale already up."
    elif [[ -n "$TS_AUTH_KEY" ]]; then
        log "[3/9] Authenticating Tailscale with auth key..."
        tailscale up --authkey="$TS_AUTH_KEY" --hostname="$TS_HOSTNAME"
    else
        log "[3/9] Tailscale NOT up. Run manually: sudo tailscale up"
    fi

    if [[ "$TS_FUNNEL" == "true" ]] && tailscale status >/dev/null 2>&1; then
        log "[3/9] Enabling Funnel for API port $API_PORT..."
        tailscale funnel --bg "$API_PORT" >/dev/null 2>&1 || log "[3/9] WARN: could not enable Funnel (may need tailscale up first)."
    fi
}

# ── 4. Shared Docker network ────────────────────────────────────────
create_network() {
    log "[4/9] Ensuring external network '$HOMELAB_NETWORK'..."

    if docker network inspect "$HOMELAB_NETWORK" >/dev/null 2>&1; then
        log "[4/9] Network '$HOMELAB_NETWORK' already exists."
    else
        docker network create --driver bridge --subnet "$HOMELAB_SUBNET" "$HOMELAB_NETWORK"
        log "[4/9] Network created."
    fi
}

# ── 5. Persistent data directories ──────────────────────────────────
create_dirs() {
    log "[5/9] Creating persistent data directories under $DATA_ROOT..."

    mkdir -p "$DATA_ROOT"
    for service in traefik portainer homepage n8n uptime-kuma duckdns; do
        mkdir -p "$DATA_ROOT/$service"
    done

    chown -R "$TARGET_USER":"$TARGET_USER" "$DATA_ROOT"
    log "[5/9] Data directories OK."
}

# ── 6. Install systemd units (backup, duckdns, firewall) ────────────
install_systemd_units() {
    log "[6/9] Installing systemd units..."

    cp "$REPO_DIR/backup/backup.service" /etc/systemd/system/backup.service
    cp "$REPO_DIR/backup/backup.timer"    /etc/systemd/system/backup.timer

    cp "$REPO_DIR/scripts/duckdns/duckdns.service" /etc/systemd/system/duckdns.service
    cp "$REPO_DIR/scripts/duckdns/duckdns.timer"   /etc/systemd/system/duckdns.timer
    cp "$REPO_DIR/scripts/duckdns/duckdns.sh"      /usr/local/bin/duckdns.sh
    chmod +x /usr/local/bin/duckdns.sh

    cp "$REPO_DIR/compose/firewall/restore-docker-user.sh"       /usr/local/sbin/restore-docker-user.sh
    cp "$REPO_DIR/compose/firewall/docker-user-restore.service"  /etc/systemd/system/docker-user-restore.service
    chmod +x /usr/local/sbin/restore-docker-user.sh

    systemctl daemon-reload
    systemctl enable backup.timer duckdns.timer docker-user-restore.service
    log "[6/9] Systemd units installed and enabled."
}

# ── 7. Firewall ─────────────────────────────────────────────────────
apply_firewall() {
    log "[7/9] Applying DOCKER-USER firewall rules..."
    systemctl restart docker-user-restore.service
    log "[7/9] Firewall applied."
}

# ── 8. Deploy compose stacks ────────────────────────────────────────
deploy_compose() {
    log "[8/9] Deploying compose stacks..."

    local compose_dirs=(
        "$REPO_DIR/compose/traefik"
        "$REPO_DIR/compose/api"
        "$REPO_DIR/compose/homepage"
        "$REPO_DIR/compose/portainer"
        "$REPO_DIR/compose/n8n"
        "$REPO_DIR/compose/uptime-kuma"
    )

    for dir in "${compose_dirs[@]}"; do
        if [[ -f "$dir/compose.yaml" ]]; then
            log "[8/9] Deploying $(basename "$dir")..."
            run_as_user docker compose --project-directory "$dir" -f "$dir/compose.yaml" up -d --remove-orphans
        fi
    done
    log "[8/9] Compose stacks deployed."
}

# ── 9. Verification ─────────────────────────────────────────────────
verify() {
    log "[9/9] Verifying deployment..."

    sleep 3
    local expected=(traefik api homepage portainer n8n uptime-kuma)
    local failed=0

    for name in "${expected[@]}"; do
        if docker ps --format '{{.Names}}' | grep -qx "$name"; then
            log "  OK: $name is running"
        else
            log "  FAIL: $name is NOT running"
            failed=1
        fi
    done

    if [[ $failed -eq 1 ]]; then
        log "Verification failed. Check: journalctl -u docker-user-restore, docker logs <container>"
    else
        log "All services are running."
    fi
}

# ── Secrets decryption (GPG vault) ──────────────────────────────────
decrypt_secrets() {
    if [[ -n "$GPG_RECIPIENT" && -x "$REPO_DIR/secrets/decrypt.sh" ]]; then
        log "Decrypting secrets vault (GPG recipient: $GPG_RECIPIENT)..."
        if "$REPO_DIR/secrets/decrypt.sh" --recipient "$GPG_RECIPIENT" --repo "$REPO_DIR"; then
            log "Secrets decrypted."
        else
            log "WARN: secret decryption failed. Check GPG key availability."
        fi
    else
        log "Skipping secrets decryption (no GPG_RECIPIENT configured or no decrypt.sh)."
    fi
}

# ── Main ────────────────────────────────────────────────────────────
base_packages
install_docker
install_tailscale
create_network
create_dirs
install_systemd_units
apply_firewall
decrypt_secrets
deploy_compose
verify

log "=== Bootstrap completed ==="
log "Next steps:"
log "  1. Restore persistent data from backup (if any):"
log "     tar -xzf <backup.tar.gz> -C $TARGET_HOME"
log "  2. Verify: curl http://127.0.0.1:3000 (Homepage), docker ps"
log "  3. If GPG vault was not decrypted, run: $REPO_DIR/secrets/decrypt.sh"
