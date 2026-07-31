# Backups

## Descripción

Backup automático diario de los datos del homelab:
- `~/homelab-data/` — datos persistentes de contenedores (Portainer, n8n, Uptime Kuma, Homepage)
- `~/homelab-docs/` — documentación y configuraciones del repositorio

## Estrategia

| Aspecto          | Detalle                                       |
|------------------|-----------------------------------------------|
| Herramientas     | `tar` + `gzip` (compresión estándar)           |
| Formato          | `homelab-YYYY-MM-DD-HHMMSS.tar.gz`            |
| Destino          | `/home/administrador/backups/`                |
| Programación     | Systemd timer — diario a las 03:00 ±5 min     |
| Integridad SQL   | Parada breve de n8n, uptime-kuma y portainer  |
| Retención        | 7 diarios + 4 semanales (domingos)            |
| Verificación     | Docker disponible, destino existe, contenedores restaurados |

## Limitaciones

**Este backup es local y no protege contra fallo del SSD.**
- Almacena en el mismo disco físico (`/dev/sda4`)
- No protege ante: fallo del disco, borrado accidental del directorio, desastre físico
- Para protección real, se necesita: disco externo USB, montar partición NTFS secundaria, o rsync remoto

## Permisos

`backup.service` ejecuta el script como **root** (`User=root`). Decisión consciente:

- Los datos persistentes de Portainer (`~/homelab-data/portainer/`) son propiedad de `root:root` con permisos restrictivos (`-rw-------`). El usuario `administrador` no puede leerlos.
- El resto de servicios (n8n, uptime-kuma, homepage) tienen directorios con permisos mundo-legibles.
- Ejecutar como root es seguro en este contexto: el backup es local, programado, sin exposición externa, y el script solo lee/escribe en rutas controladas.

## Archivos

| Archivo           | Propósito                        |
|-------------------|----------------------------------|
| `backup.sh`       | Script principal                 |
| `backup.service`  | Systemd service unit             |
| `backup.timer`    | Systemd timer unit               |

## Exclusiones

El script excluye los siguientes archivos y directorios del backup:

| Exclusión | Motivo |
|-----------|--------|
| `homelab-docs/.git` | Repositorio remoto ya existe en GitHub |
| `*.env` (cualquier `.env` de `homelab-data/` y `homelab-docs/`) | Contienen credenciales (API, n8n) |
| `homelab-data/duckdns/duckdns.conf` | Contiene el token de DuckDNS |
| `homelab-data/portainer/certs` | Certificados efímeros regenerables |
| `homelab-data/portainer/bin` | Binarios descargables |
| `homelab-data/portainer/compose` | Stacks de Portainer (en git) |
| `homelab-data/portainer/tls` | Certificados TLS regenerables |
| `homelab-data/portainer/chisel` | Tunnel efímero |

Nota: antes del 30-07-2026 los backups incluían `compose/n8n/.env` y `compose/api/.env`. Los backups afectados fueron eliminados y regenerados sin credenciales.

## Instalación

```bash
sudo cp backup/backup.service backup/backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now backup.timer
```

## Prueba manual

```bash
sudo systemctl start backup.service
journalctl -u backup.service -f
```

## Restauración

```bash
tar -xzf /home/administrador/backups/homelab-<fecha>.tar.gz -C /home/administrador
```

Esto extrae `homelab-data/` y `homelab-docs/` en `/home/administrador/`.

## Mejoras futuras

- [ ] Backup a disco externo USB
- [ ] Backup cifrado con GPG
- [ ] Notificaciones (webhook, Telegram, Uptime Kuma)
- [ ] Backup de `/etc/` y configs del sistema
- [ ] Verificación de integridad post-backup
- [ ] Destino remoto vía rsync
