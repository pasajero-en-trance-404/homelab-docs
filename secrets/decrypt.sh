#!/usr/bin/env bash
# Decrypt secrets from the GPG vault back to their original locations.
#
# Usage:
#   ./secrets/decrypt.sh [--recipient KEY_ID] [--repo DIR] [--data-root DIR]
#
# Options can also come from env: GPG_RECIPIENT, REPO_DIR, DATA_ROOT.
# For symmetric vaults, gpg prompts for the passphrase.

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
    [[ -n "$vaultname" ]] || continue
    [[ "$vaultname" == *.gpg ]] || vaultname="$vaultname.gpg"

    src_resolved="$(resolve_path "$src")"
    vault_file="$VAULT_DIR/$vaultname"

    if [[ -f "$vault_file" ]]; then
        mkdir -p "$(dirname "$src_resolved")"
        if [[ -n "$GPG_PASSPHRASE" ]]; then
            gpg --batch --yes --pinentry-mode loopback --passphrase-fd 0 \
                --decrypt --output "$src_resolved" "$vault_file" <<< "$GPG_PASSPHRASE"
        else
            gpg --batch --yes --decrypt --output "$src_resolved" "$vault_file"
        fi
        chmod 600 "$src_resolved"
        echo "Decrypted: $vault_file -> $src_resolved"
        count=$((count + 1))
    else
        echo "WARN: vault file not found, skipping: $vault_file"
    fi
done < "$MANIFEST"

echo "Done. $count file(s) decrypted."
