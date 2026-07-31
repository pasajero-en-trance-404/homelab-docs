# Disaster Recovery — Runbook v1.1

> **Objetivo**: reconstruir el homelab completo en **< 30 minutos** desde cero, usando solo el repositorio git + backups.

## Índice de recuperación

| Escenario | Qué hacer |
|-----------|-----------|
| Falló el disco / máquina nueva | Runbook completo (abajo) |
| Solo se perdió Docker | Re-ejecutar `bootstrap.sh` (idempotente) |
| Solo se perdió un contenedor | `docker compose up -d` del stack afectado |
| Se perdió `~/homelab-data/` | Restaurar backup + reiniciar servicios |
| Se corrompió una config | Restaurar desde git (configs) o backup (datos) |

---

## Prerrequisitos (deben existir ANTES de un desastre)

- [ ] Repositorio clonado o disponible en GitHub
- [ ] `secrets/vault/` con los `.gpg` cifrados y versionados en git
- [ ] Clave GPG privada respaldada en lugar seguro
- [ ] Backups recientes en `/home/administrador/backups/` (o disco externo)
- [ ] Auth key efímera de Tailscale disponible (o acceso para `tailscale up` manual)

---

## Runbook completo

### Fase 0 — Preparación (5 min)

1. Instalar Debian 13 (trixie) con el usuario `administrador`.
2. Verificar red e internet: `ping 1.1.1.1`.
3. Asegurar clave SSH (si se configuró) o password temporal.

### Fase 1 — Clonar repo e instalar git (5 min)

```bash
sudo apt update && sudo apt install -y git curl
git clone https://github.com/anomalyco/homelab-docs.git ~/homelab-docs
```

### Fase 2 — Configurar secrets (2 min)

```bash
# Importar la clave GPG privada que cifra el vault
gpg --import <clave-privada.asc>

# Configurar el bootstrap
cp ~/homelab-docs/bootstrap/vars.env.example ~/homelab-docs/bootstrap/vars.env
#   Editar: TARGET_USER, TS_AUTH_KEY (opcional), GPG_RECIPIENT
```

### Fase 3 — Bootstrap (10 min)

```bash
cd ~/homelab-docs
sudo ./bootstrap/bootstrap.sh
```

Esto instala: paquetes base, Docker, Tailscale, red `homelab`, directorios de datos, systemd units, firewall y despliega los 6 stacks.

Si `GPG_RECIPIENT` está configurado, el bootstrap descifra automáticamente el vault de secretos.

### Fase 4 — Restaurar datos persistentes (5 min)

```bash
# Restaurar el backup más reciente
ls -t /home/administrador/backups/homelab-*.tar.gz | head -1
tar -xzf /home/administrador/backups/homelab-<fecha>.tar.gz -C /home/administrador
```

Si el backup está en otro lado (disco USB), copiarlo primero.

### Fase 5 — Verificar (5 min)

```bash
docker ps                     # 6 contenedores: traefik, api, homepage, portainer, n8n, uptime-kuma
tailscale status              # debian-server en el tailnet
curl http://127.0.0.1:3000    # Homepage
curl http://127.0.0.1:8000    # API local
curl https://debian-server.taile532c7.ts.net/api   # API pública (si Funnel)
journalctl -u docker-user-restore   # firewall OK
```

### Fase 6 — Post-verificación

- [ ] Portainer accesible en `http://192.168.1.50:9000`
- [ ] n8n accesible y con workflows previos
- [ ] Uptime Kuma con monitores previos
- [ ] DuckDNS actualizando (timer activo)
- [ ] Backup.timer activo para la próxima noche
- [ ] Funnel activo: `tailscale funnel status`
- [ ] Firewall: `iptables -L DOCKER-USER -n` muestra reglas + DROP

---

## Tiempo objetivo

| Fase | Tiempo |
|------|--------|
| 0. Preparación | 5 min |
| 1. Clonar repo | 5 min |
| 2. Secrets | 2 min |
| 3. Bootstrap | 10 min |
| 4. Restaurar datos | 5 min |
| 5. Verificar | 5 min |
| **Total** | **~32 min** |

*Con disco de instalación Debian ya preparado, bajaría a ~25 min.*

---

## Secrets (GPG vault)

Los archivos sensibles (`compose/api/.env`, `compose/n8n/.env`, `duckdns.conf`) no están en git en texto plano. Están cifrados en `secrets/vault/*.gpg`.

**Regenerar el vault** (desde la máquina con los secretos originales):

```bash
./secrets/encrypt.sh --recipient <KEY_ID>
```

**Descifrar manualmente** (en la máquina nueva):

```bash
./secrets/decrypt.sh --recipient <KEY_ID>
```

> ⚠️ **Sin la clave GPG privada, el vault es irrecuperable.** Respaldarla.

---

## Notas y advertencias

- El backup es **local** (mismo disco). Un fallo de disco total pierde backups y datos. La mitigación futura es backup a disco externo/remoto.
- `bootstrap.sh` es idempotente: se puede re-ejecutar sin miedo.
- El orden **bootstrap → restaurar datos** evita que los servicios arranquen sin datos y pisen configs existentes.
- Si se re-ejecuta `bootstrap.sh` sobre un sistema ya funcionando, no rompe nada (es idempotente).
