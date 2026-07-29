#!/usr/bin/env bash
set -eu

BACKUP_DIR="/home/administrador/backups"
DOCS_DIR="/home/administrador/homelab-docs"
DATA_DIR="/home/administrador/homelab-data"
RETENTION_DAILY=7
RETENTION_WEEKLY=4
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/homelab-$TIMESTAMP.tar.gz"
LOG_FILE="$BACKUP_DIR/backup.log"

# Create backup directory early so log() can write
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR" 2>/dev/null || {
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] FATAL: Cannot create $BACKUP_DIR" >&2
        exit 1
    }
fi

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE" 2>/dev/null || echo "$msg" >&2
}

error_exit() {
    log "ERROR: $*"
    for c in portainer uptime-kuma n8n; do
        docker start "$c" &>/dev/null || true
    done
    exit 1
}

# === VERIFICATION: Docker ===
log "=== Backup started ==="

if ! command -v docker &>/dev/null; then
    error_exit "Docker not found"
fi

if ! docker info &>/dev/null; then
    error_exit "Docker daemon not running"
fi

# === STOP containers with SQLite data ===
log "Stopping containers for data consistency..."
for c in n8n uptime-kuma portainer; do
    if docker ps --format '{{.Names}}' | grep -qx "$c"; then
        docker stop "$c" &>/dev/null || log "WARN: could not stop $c"
    else
        log "WARN: $c not running, skipping stop"
    fi
done

# Wait for containers to fully stop (SQLite WAL flush)
for c in n8n uptime-kuma portainer; do
    waited=0
    while [ "$waited" -lt 15 ]; do
        state=$(docker inspect "$c" --format '{{.State.Status}}' 2>/dev/null || echo "missing")
        [ "$state" = "exited" ] && break
        sleep 1
        waited=$((waited + 1))
    done
    if [ "$waited" -ge 15 ]; then
        log "WARN: $c did not stop within 15s, proceeding anyway"
    fi
done

# === BACKUP: data + docs ===
log "Creating backup: $(basename "$BACKUP_FILE")"

tar -czf "$BACKUP_FILE" \
    --exclude='homelab-docs/.git' \
    --exclude='homelab-docs/compose/n8n/.env' \
    --exclude='homelab-data/portainer/certs' \
    --exclude='homelab-data/portainer/bin' \
    --exclude='homelab-data/portainer/compose' \
    --exclude='homelab-data/portainer/tls' \
    --exclude='homelab-data/portainer/chisel' \
    --ignore-failed-read \
    -C /home/administrador \
    homelab-data homelab-docs || error_exit "Backup creation failed"

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "Backup size: $BACKUP_SIZE"

# === RESTART containers ===
log "Restarting containers..."
for c in portainer uptime-kuma n8n; do
    docker start "$c" &>/dev/null || log "WARN: could not start $c"
done

# === VERIFY containers ===
log "Verifying containers..."
sleep 3
ALL_OK=true
for c in homepage portainer uptime-kuma n8n; do
    if docker ps --format '{{.Names}}' | grep -qx "$c"; then
        log "  OK: $c is running"
    else
        log "  FAIL: $c is NOT running"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = false ]; then
    error_exit "Not all containers restarted"
fi

# === PRUNE ===
log "Pruning old backups..."
python3 -c "
import os, glob
from datetime import datetime

backup_dir = '$BACKUP_DIR'
files = sorted(glob.glob(os.path.join(backup_dir, 'homelab-*.tar.gz')))
now = datetime.now()
kept = 0
deleted = 0

for f in files:
    basename = os.path.basename(f)
    parts = basename.replace('homelab-', '').replace('.tar.gz', '').split('-')
    try:
        dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        continue
    age = (now - dt).days

    if age <= $RETENTION_DAILY:
        kept += 1
        continue

    if age <= 28 and dt.weekday() == 6:
        kept += 1
        continue

    os.remove(f)
    deleted += 1

print(f'Prune: kept {kept}, deleted {deleted}')
" 2>&1 | tee -a "$LOG_FILE"

log "=== Backup completed ==="
log ""
