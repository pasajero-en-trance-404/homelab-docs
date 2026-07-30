# AGENTS.md — Contexto para Agentes de IA

## Descripción general

Este repositorio documenta y configura un servidor homelab personal. El servidor físico corre Debian 13 (Trixie) y utiliza Docker + Docker Compose como plataforma de servicios. Este repositorio contiene documentación, archivos compose y configuraciones. Los datos persistentes se almacenan fuera del repositorio.

## Objetivo del servidor

Convertir una PC antigua (AMD A4-4000, 4 GB RAM, SSD 120 GB) en una plataforma personal para:
- Aprender Linux, Docker, redes y automatización
- Ejecutar servicios self-hosted (monitoreo, automatización, paneles)
- Alojar APIs, automatizaciones, agentes de IA y servicios propios
- Documentar todo el proceso paso a paso

## Arquitectura actual

```
Internet
  └─ Tailscale (100.119.176.84/32)
       └─ Servidor Debian 13 (192.168.1.50/24)
            ├─ SSH (22)              ⬥ Solo key, sin root
            ├─ Firewall DOCKER-USER  ⬥ Bloquea LAN no autorizada
            └─ Docker Engine (29.6.2)
                 ├─ Portainer (9000)      ⬥ Administración de contenedores
                 ├─ Homepage (3000)       ⬥ Dashboard de servicios
                 ├─ n8n (5678)            ⬥ Automatización low-code
                 └─ Uptime Kuma (3001)    ⬥ Monitoreo de uptime
```

Todos los servicios comparten la red `homelab` (external: true, 172.22.0.0/16). No hay reverse proxy ni SSL configurado aún. El acceso externo es exclusivamente por Tailscale.

## Estructura de carpetas

```
~/homelab-docs/                 ← Este repositorio (git)
├── AGENTS.md                   ← Contexto para agentes de IA
├── README.md                   ← Documentación principal
├── CHANGELOG.md                ← Historial de cambios
├── 00-estado-inicial.md        ← Estado del equipo al comenzar
├── 01-hardware.md              ← Especificaciones de hardware
├── 02-instalacion-debian.md    ← Instalación de Debian 13
├── 03-sistema-base.md          ← Configuración base del sistema
├── 04-docker.md                ← Instalación de Docker
├── 05-red.md                   ← Configuración de red, firewall, SSH
├── 06-servicios.md             ← Servicios instalados
├── 07-automatizacion.md        ← Automatizaciones
├── 08-problemas.md             ← Problemas encontrados y soluciones
├── 09-comandos-utiles.md       ← Comandos de referencia
├── backup/
│   ├── backup.sh               ← Script de backup automático
│   ├── backup.service          ← Systemd service unit
│   ├── backup.timer            ← Systemd timer (diario 03:00)
│   └── README.md               ← Documentación del sistema de backups
├── docs/
│   └── architecture.md         ← Arquitectura general del homelab
├── assets/
│   ├── diagramas/
│   ├── fotos/
│   └── screenshots/
└── compose/                    ← Archivos Docker Compose
    ├── firewall/
    │   ├── restore-docker-user.sh       ← Script de restauración del firewall
    │   └── docker-user-restore.service  ← Systemd service unit
    ├── homepage/
    │   ├── compose.yaml
    │   └── services.yaml       ← Config de Homepage dashboard
    ├── n8n/
    │   ├── .env                ← Variables de entorno
    │   └── compose.yaml
    ├── portainer/
    │   └── compose.yaml
    └── uptime-kuma/
        └── compose.yaml
```

## Servicios instalados

| Servicio   | Imagen                              | Puerto   | Estado       |
|------------|-------------------------------------|----------|--------------|
| Portainer  | portainer/portainer-ce:latest       | 9000     | Up           |
| Homepage   | ghcr.io/gethomepage/homepage:latest | 3000     | Up (healthy) |
| n8n        | docker.n8n.io/n8nio/n8n:latest      | 5678     | Up           |
| Uptime Kuma| louislam/uptime-kuma:latest         | 3001     | Up (healthy) |

## Puertos utilizados

- 22: SSH (solo key, sin password)
- 3000: Homepage (dashboard)
- 3001: Uptime Kuma (monitoreo)
- 5678: n8n (automatización)
- 9000: Portainer (administración)

## Ubicación de datos persistentes

Todos los datos persistentes viven bajo `/home/administrador/homelab-data/`:

| Servicio   | Ruta                                           |
|------------|-------------------------------------------------|
| Portainer  | ~/homelab-data/portainer                        |
| Homepage   | ~/homelab-data/homepage                         |
| n8n        | ~/homelab-data/n8n                              |
| Uptime Kuma| ~/homelab-data/uptime-kuma                      |

Convención: `~/homelab-data/<nombre-servicio>/`

## Convenciones para agregar nuevos servicios

1. Crear carpeta en `compose/<nombre>/`
2. Usar `compose.yaml` (no `docker-compose.yml`)
3. Nombrar el container con `container_name: <nombre>`
4. Usar `restart: unless-stopped`
5. Conectar a la red externa `homelab`
6. Usar bind mounts a `~/homelab-data/<nombre>/` para datos persistentes
7. Si necesita variables de entorno, usar `.env` dentro de su carpeta
8. Registrar el servicio en `compose/homepage/services.yaml`
9. Agregar entrada en 06-servicios.md
10. No exponer puertos innecesarios

## Firewall

El firewall usa reglas `iptables-nft` en la cadena `DOCKER-USER`. No hay UFW. La política INPUT sigue en ACCEPT.

### Reglas activas

Agregadas en `DOCKER-USER` (cadena de admin que Docker preserva):

1. `ctstate RELATED,ESTABLISHED` — mantener conexiones activas
2. `-i tailscale0` — permitir todo desde Tailscale
3. `-i br+/docker0 dport 53 (udp+tcp)` — DNS desde contenedores
4. `-i br+/docker0 dport 80,443` — HTTP/HTTPS desde contenedores
5. `-i br+/docker0 icmp` — ping desde contenedores
6. `-s 192.168.1.0/24 dport 3000` — Homepage desde LAN
7. DROP — todo lo demás bloqueado

### Persistencia

Las reglas se restauran al boot via systemd:

| Componente | Ruta |
|------------|------|
| Script | `/usr/local/sbin/restore-docker-user.sh` |
| Service | `/etc/systemd/system/docker-user-restore.service` |
| Snapshot | `/etc/iptables/rules.v4.backup` |
| Fuente repo | `compose/firewall/` |

Restaurar manualmente: `sudo systemctl restart docker-user-restore.service`

Para modificar reglas: editar `compose/firewall/restore-docker-user.sh`, ejecutar manualmente, verificar, actualizar snapshot.

## Reglas de seguridad

- No comitear `.env` ni archivos con credenciales al repositorio (`.env` ya está en `.gitignore`)
- No exponer puertos de administración a Internet sin reverse proxy o tunnel
- Los agentes de IA no deben modificar datos en `~/homelab-data/`
- Los agentes no deben ejecutar comandos destructivos sin confirmación explícita del usuario
- Preferir imágenes oficiales y verificar fuentes
- Usar redes Docker internas para comunicación entre servicios

## Reglas para modificar Docker Compose

- Editar `compose.yaml` existente, no crear archivos duplicados
- No eliminar ni modificar volúmenes bind existentes sin preguntar
- Documentar cambios relevantes en los archivos markdown correspondientes
- No cambiar puertos expuestos sin coordinar con el resto del stack
- Probar la sintaxis con `docker compose config` después de cada cambio

## Reglas para manejo de volúmenes

- No eliminar volúmenes ni datos sin confirmación explícita del usuario
- Preferir bind mounts (`~/homelab-data/<servicio>/:/ruta/en/container`) sobre named volumes de Docker
- Los datos persistentes NUNCA deben estar dentro del repositorio git
- Si se migra un servicio, preservar la carpeta de datos correspondiente

## Backups

Existe un sistema automático de backups programado con systemd timer:

| Aspecto          | Detalle                                              |
|------------------|------------------------------------------------------|
| Script           | `backup/backup.sh`                                   |
| Timer            | `backup.timer` — diario a las 03:00 ±5 min           |
| Destino          | `/home/administrador/backups/`                       |
| Contenido        | `~/homelab-data/` + `~/homelab-docs/`                |
| Compresión       | `tar -czf` (gzip)                                    |
| Retención        | 7 backups diarios + 4 semanales (domingos)            |
| Formato archivo  | `homelab-YYYY-MM-DD-HHMMSS.tar.gz`                   |
| Ejecución        | `User=root` (permisos de Portainer requieren root)    |

**Limitación**: el destino está en el mismo disco físico (`/dev/sda4`). No protege contra fallo del SSD.

**Pendiente futuro**: backup a disco externo USB o destino remoto (rsync, rsync.net, BorgBase).

No modificar los archivos de backup sin entender el flujo completo (stop de contenedores SQLite, restart, verificación).

## Buenas prácticas para agentes

- Leer este archivo al inicio de cada sesión
- La documentación está en español — mantener consistencia
- Preferir soluciones simples, mantenibles y bien documentadas
- Cada servicio debe tener su propia carpeta dentro de `compose/`
- No asumir que un servicio está funcionando; verificar con `docker ps`
- Si se rompe algo, detenerse y consultar antes de continuar
- Agregar entradas a `08-problemas.md` cuando se encuentren errores
- Registrar cambios significativos en el README si corresponde

## Roadmap futuro

- [x] Tailscale — acceso remoto a la red
- [x] SSH hardening — solo key auth, sin root, sin X11
- [x] Firewall (DOCKER-USER) — bloqueo de LAN no autorizada
- [x] Sistema de backups automáticos
- [ ] Cloudflare Tunnel — publicación segura de servicios
- [ ] Reverse proxy (Traefik o Nginx Proxy Manager) — TLS, dominios
- [ ] OpenCode — agente de IA local
- [ ] Base de datos (PostgreSQL, SQLite)
- [ ] Monitoreo y alertas (Prometheus + Grafana?)
- [ ] APIs y servicios propios desplegados como contenedores
- [ ] Posible ampliación de RAM a 8 GB

## Notas adicionales

- Usuario del sistema: `administrador`
- IP estática: `192.168.1.50/24`
- Gateway: `192.168.1.1`
- DNS: `192.168.1.1`, `1.1.1.1`
- Shell por defecto: bash
- Zona horaria: `America/Argentina/Buenos_Aires`
- Docker Engine 29.6.2 | Docker Compose v5.3.1
- Acceso SSH solo por clave, sin password, sin root
- Portainer fue migrado de `docker-compose.yml` a `compose.yaml` durante la limpieza del repositorio. El archivo legacy fue reemplazado.
