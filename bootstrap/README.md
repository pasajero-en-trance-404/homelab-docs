# Bootstrap

Script idempotente que reconstruye todo el homelab desde una instalación limpia de **Debian 13**.

## Uso

```bash
# 1. Configurar (opcional, ver vars.env.example)
cp bootstrap/vars.env.example bootstrap/vars.env
#    Ajustar valores (usuario, IP, TS_AUTH_KEY, GPG_RECIPIENT, etc.)

# 2. Ejecutar como root
sudo ./bootstrap/bootstrap.sh
```

## Qué hace

| Paso | Acción |
|------|--------|
| 1 | Instala paquetes base (curl, git, gnupg, iptables, openssl...) |
| 2 | Instala Docker Engine + Compose plugin (repo oficial) |
| 3 | Instala Tailscale y autentica (auth key efímera o manual) |
| 4 | Crea la red externa `homelab` (172.22.0.0/16) |
| 5 | Crea directorios de datos en `~/homelab-data/` |
| 6 | Instala units systemd (backup, duckdns, firewall) |
| 7 | Aplica reglas DOCKER-USER del firewall |
| 8 | Despliega los 6 stacks con `docker compose up -d` |
| 9 | Verifica que todos los contenedores estén corriendo |

## Idempotencia

El script es seguro de re-ejecutar: cada paso detecta si ya está hecho y lo saltea.
Es la base del objetivo "reconstruir en <30 min".

## Orden de operación para disaster recovery

1. Instalar Debian 13 limpio.
2. Instalar git y clonar el repositorio.
3. Ejecutar `sudo ./bootstrap/bootstrap.sh`.
4. Restaurar datos persistentes desde el backup.
5. Descifrar el vault GPG si `GPG_RECIPIENT` está configurado.

## Variables

Todas son opcionales (hay defaults). Ver `vars.env.example` para la lista completa.

| Variable | Default | Descripción |
|----------|---------|-------------|
| `TARGET_USER` | `administrador` | Usuario del sistema |
| `DATA_ROOT` | `~/homelab-data` | Datos persistentes |
| `TS_AUTH_KEY` | *(vacío)* | Auth key efímera de Tailscale |
| `TS_FUNNEL` | `true` | Re-habilitar Funnel para la API |
| `GPG_RECIPIENT` | *(vacío)* | Key GPG del vault de secretos |
