# Secrets — GPG Vault

Vault de secretos cifrado con GPG para que los archivos sensibles sobrevivan a un reinstall sin quedar en texto plano en git.

## Cómo funciona

Los archivos sensibles se cifran y se guardan como `.gpg` en `secrets/vault/`.
El `manifest` mapea cada archivo original a su nombre cifrado.

| Archivo | Contenido |
|---------|-----------|
| `manifest` | Lista de archivos a cifrar (ruta origen → nombre `.gpg`) |
| `vault/` | Archivos cifrados (se versionan en git) |
| `encrypt.sh` | Cifra los archivos del manifest |
| `decrypt.sh` | Restaura los archivos originales desde el vault |

Los archivos originales (`compose/api/.env`, `compose/n8n/.env`, `duckdns.conf`) **nunca se versionan** (están en `.gitignore`).

## Uso

### 1. Preparar el recipient GPG

```bash
gpg --full-generate-key          # crear una key si no tenés
gpg --list-secret-keys           # anotar el key ID
```

### 2. Cifrar los secretos

```bash
./secrets/encrypt.sh --recipient <KEY_ID>
```

También se puede usar `GPG_RECIPIENT=<KEY_ID> ./secrets/encrypt.sh`.
Sin recipient, usa cifrado simétrico (pide passphrase).

### 3. Descifrar (restaurar)

```bash
./secrets/decrypt.sh --recipient <KEY_ID>
```

El bootstrap lo hace automáticamente si `GPG_RECIPIENT` está configurado en `bootstrap/vars.env`.

## Notas de seguridad

- La clave privada GPG debe respaldarse aparte (ej. en un gestor de contraseñas). Sin ella, el vault es irrecuperable.
- La passphrase del recipient se pide en cada cifrado/descifrado.
- Los archivos descifrados se crean con permisos `600`.
- No commitear archivos `.env` ni `duckdns.conf` en texto plano.
