# Changelog

Todas las fechas en `YYYY-MM-DD`.

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
