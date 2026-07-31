# Changelog

Todas las fechas en `YYYY-MM-DD`.

## [2026-07-30] — Auditoría de documentación v1.0

### Corregido
- `AGENTS.md` — agregado `docs/public-access.md` al árbol de directorios (faltaba)
- `backup/README.md` — documentación de `pigz` corregida a `gzip`; agregada tabla de exclusiones de Portainer
- `01-hardware.md` — nota sobre VRAM reservada por la APU; partición Debian unificada a `65 GB`
- `README.md` — partición sistema corregida de `60 GB` a `65 GB`

## [2026-07-30] — API pública con Tailscale Funnel

### Agregado
- Servicio API: `compose/api/` con FastAPI, Dockerfile y compose.yaml
- Endpoints: `GET /api`, `GET /api/health`
- Middleware X-API-Key para endpoints protegidos futuros
- Documentación de acceso público: `docs/public-access.md`
- Integración con Tailscale Funnel para exposición pública sin abrir puertos

### Modificado
- `AGENTS.md` — arquitectura actualizada con Funnel + API, tabla de servicios con columna de acceso, sección de exposición pública, roadmap
- `README.md` — sección Servicios públicos, roadmap actualizado
- `06-servicios.md` — API agregada a tabla de servicios y puertos
- `compose/homepage/services.yaml` — API agregada al dashboard
- `docs/architecture.md` — diagrama con Funnel, tabla de acceso público/privado

## [2026-07-30] — Endpoint /api/status con monitoreo Docker

### Agregado
- Endpoint `GET /api/status` — estado de contenedores vía Docker socket (read-only)
- `compose/api/main.py` — función `_docker_state()` consulta Docker API con Unix socket
- Montaje de `/var/run/docker.sock:ro` en `compose/api/compose.yaml`
- Detección dinámica del hostname con `socket.gethostname()`
- Manejo de errores: si Docker socket no responde, estado "unknown"

### Modificado
- `docs/public-access.md` — documentación de `/api/status`, riesgos de Docker socket
- `docs/architecture.md` — nota sobre Docker socket en la API
- `CHANGELOG.md` — esta entrada

## [2026-07-30] — DuckDNS con actualización automática via systemd

### Agregado
- Script DuckDNS: `scripts/duckdns/duckdns.sh` con lectura segura de token desde `~/homelab-data/`
- Systemd oneshot service: `scripts/duckdns/duckdns.service`
- Systemd timer: `scripts/duckdns/duckdns.timer` (cada 5 minutos, con retardo aleatorio)
- Template de configuración: `scripts/duckdns/.env.example`
- Dominio configurado: `homelab404-debian.duckdns.org` → IP pública actualizada

### Modificado
- `docs/public-access.md` — sección DuckDNS completa: setup, verificación, troubleshooting
- `AGENTS.md` — estructura de carpetas actualizada con `scripts/`, roadmap con DuckDNS
- `README.md` — servicios públicos actualizados con DuckDNS

## [2026-07-29] — Firewall persistente y documentación

### Agregado
- Reglas DOCKER-USER (14 reglas): bloqueo LAN excepto Homepage, permitir Tailscale, salida contenedores por puertos esenciales
- Script de restore: `/usr/local/sbin/restore-docker-user.sh` con wait loop, flock y logging
- Servicio systemd: `docker-user-restore.service` (After=docker.service, Requires=docker.service)
- Snapshot de iptables: `/etc/iptables/rules.v4.backup`
- Documentación de firewall, Tailscale y SSH en `05-red.md`
- Archivo `docs/architecture.md` con diagrama general
- Archivo `CHANGELOG.md`

### Modificado
- `05-red.md` — secciones completas de Tailscale, firewall (DOCKER-USER), SSH hardening
- `AGENTS.md` — arquitectura actualizada con Tailscale y firewall, secciones de firewall y backups
- `README.md` — roadmap actualizado con tareas completadas, hardware real, documentación actualizada
- `06-servicios.md` — notas sobre protección por firewall
- `07-automatizacion.md` — sección "Próximos workflows"
- `08-problemas.md` — 6 incidencias documentadas
- `09-comandos-utiles.md` — categorías: firewall, tailscale, ssh, backups

### Corregido
- Red de n8n: migrada de `n8n_default` a `homelab` (2026-07-28)
- Permisos root de Portainer: backup script corre como `User=root`

## [2026-07-29] — Sistema de backups

### Agregado
- Script de backup: `backup/backup.sh`
- Systemd service: `backup.service` (User=root)
- Systemd timer: `backup.timer` (diario 03:00)
- Documentación en `backup/README.md`
- Sección Backups en `AGENTS.md`

### Comportamiento
- Backup: detiene n8n/uptime-kuma/portainer, comprime datos + docs, re-inicia, verifica
- Retención: 7 diarios + 4 semanales (domingos)
- Limitación: destino en el mismo disco físico

## [2026-07-28] — Migración a compose.yaml y limpieza de docs

### Modificado
- Todos los servicios migrados de `docker-compose.yml` a `compose.yaml`
- Archivo legacy `portainer/docker-compose.yml` marcado como no usar
- Documentación reestructurada: AGENTS.md, 06-servicios.md, 07-automatizacion.md, 09-comandos-utiles.md
- README.md actualizado con estructura del proyecto

### Agregado
- Variables de entorno en `compose/n8n/.env`
- Services.yaml de Homepage con 4 servicios

## [2026-07-27] — Configuración inicial

### Agregado
- Instalación de Debian 13 (Trixie) + XFCE
- Dual Boot con Windows
- Docker Engine 29.6.2 + Compose v5.3.1
- Portainer en compose.yaml
- Homepage en compose.yaml
- n8n en compose.yaml
- Uptime Kuma en compose.yaml
- Repositorio git inicializado
- README.md, AGENTS.md, 00-estado-inicial.md a 09-comandos-utiles.md creados
- Red externa `homelab` creada
- SSH configurado y verificado
