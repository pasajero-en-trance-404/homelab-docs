#!/usr/bin/env bash
# Encrypt secrets listed in the manifest into the GPG vault.
#
# Usage:
#   ./secrets/encrypt.sh [--recipient KEY_ID] [--repo DIR] [--data-root DIR]
#
# Options can also come from env: GPG_RECIPIENT, REPO_DIR, DATA_ROOT.
# Falls back to symmetric (passphrase) encryption when no recipient is set.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DATA_ROOT="${DATA_ROOT:-$HOME/homelab-data}"
GPG_RECIPIENT="${GPG_RECIPIENT:-}"
GPG_PASSPHRASE="${GPG_PASSPHRASE:-}"
VAULT_DIR="$SCRIPT_DIR/vault"
MANIFEST="$SCRIPT_DIR/manifest"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --recipient)  GPG_RECIPIENT="$2"; shift 2 ;;
        --repo)       REPO_DIR="$2"; shift 2 ;;
        --data-root)  DATA_ROOT="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

[[ -f "$MANIFEST" ]] || { echo "ERROR: manifest not found: $MANIFEST" >&2; exit 1; }
command -v gpg >/dev/null 2>&1 || { echo "ERROR: gpg is required" >&2; exit 1; }

mkdir -p "$VAULT_DIR"

gpg_encrypt() {
    local src="$1" out="$2"
    if [[ -n "$GPG_RECIPIENT" ]]; then
        gpg --batch --yes --trust-model always --encrypt --recipient "$GPG_RECIPIENT" --output "$out" "$src"
    elif [[ -n "$GPG_PASSPHRASE" ]]; then
        gpg --batch --yes --pinentry-mode loopback --passphrase-fd 0 \
            --symmetric --cipher-algo AES256 --output "$out" "$src" <<< "$GPG_PASSPHRASE"
    else
        gpg --batch --yes --symmetric --cipher-algo AES256 --output "$out" "$src"
    fi
}

resolve_path() {
    local p="$1"
    p="${p//\{DATA_ROOT\}/$DATA_ROOT}"
    p="${p//\{REPO\}/$REPO_DIR}"
    if [[ "$p" = /* ]]; then
        echo "$p"
    else
        echo "$REPO_DIR/$p"
    fi
}

count=0
while IFS=$'\t' read -r src vaultname || [[ -n "$src" ]]; do
    [[ -z "$src" || "$src" =~ ^# ]] && continue
    [[ -n "$vaultname" ]] || { echo "ERROR: manifest line without vault name: $src" >&2; exit 1; }
    [[ "$vaultname" == *.gpg ]] || vaultname="$vaultname.gpg"

    src_resolved="$(resolve_path "$src")"
    out="$VAULT_DIR/$vaultname"

    if [[ -f "$src_resolved" ]]; then
        gpg_encrypt "$src_resolved" "$out"
        echo "Encrypted: $src_resolved -> $out"
        count=$((count + 1))
    else
        echo "WARN: source not found, skipping: $src_resolved"
    fi
done < "$MANIFEST"

echo "Done. $count file(s) encrypted into $VAULT_DIR"
