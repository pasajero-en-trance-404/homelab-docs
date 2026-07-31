# Servicios instalados

## Plataforma

- Docker Engine: 29.6.2
- Docker Compose: v5.3.1
- Red compartida: `homelab` (external bridge, 172.22.0.0/16)

## Servicios

| Servicio    | Imagen                                    | Puerto  | Estado               | Red      | Ruta de datos                             |
|-------------|-------------------------------------------|---------|----------------------|----------|--------------------------------------------|
| Traefik     | traefik:v3.7                              | 80/8080 | Up                   | homelab  | ~/homelab-data/traefik                     |
| API         | build local (Dockerfile)                  | 8000    | Up                   | homelab  | compose/api/.env (sin datos persistentes)  |
| Portainer   | portainer/portainer-ce:latest             | 9000    | Up                   | homelab  | ~/homelab-data/portainer                   |
| Homepage    | ghcr.io/gethomepage/homepage:latest       | 3000    | Up (healthy)         | homelab  | ~/homelab-data/homepage                    |
| n8n         | docker.n8n.io/n8nio/n8n:latest            | 5678    | Up                   | homelab  | ~/homelab-data/n8n                         |
| Uptime Kuma | louislam/uptime-kuma:latest               | 3001    | Up (healthy)         | homelab  | ~/homelab-data/uptime-kuma                 |

## Puertos utilizados

| Puerto | Servicio    | Uso                        |
|--------|-------------|----------------------------|
| 22     | SSH         | Acceso remoto              |
| 80     | Traefik     | Reverse proxy (localhost)  |
| 8000   | API         | API pública (FastAPI)      |
| 3000   | Homepage    | Dashboard                  |
| 3001   | Uptime Kuma | Monitoreo de uptime        |
| 5678   | n8n         | Automatización             |
| 8080   | Traefik     | Dashboard (localhost)      |
| 9000   | Portainer   | Admin. contenedores        |

## Red

- Interfaz: enp3s0
- IP: 192.168.1.50/24
- Gateway: 192.168.1.1
- DNS: 192.168.1.1, 1.1.1.1

## Notas

- Portainer, Uptime Kuma y Homepage exponen el puerto del host mapeado 1:1.
- Traefik es el reverse proxy central con host-based routing (`*.homelab`). Escucha en `127.0.0.1:80` (HTTP) y `127.0.0.1:8080` (dashboard). Ver `docs/traefik.md`.
- Los servicios se acceden por Traefik con `Host: <servicio>.homelab` en `127.0.0.1`; los puertos directos se mantienen.
- n8n usa la variable `${N8N_PORT}` definida en `compose/n8n/.env`.
- La API expone el puerto 8000 solo en localhost (`127.0.0.1:8000:8000`) — no es accesible desde LAN directamente. Se expone públicamente mediante Tailscale Funnel.
- Homepage tiene acceso al socket de Docker para mostrar contenedores en el dashboard.
- Los servicios están protegidos por el firewall DOCKER-USER. Solo Homepage (3000) es accesible desde la LAN. El resto solo responde por Tailscale.
- Todos los servicios se acceden por Tailscale desde fuera de la LAN. Ver `05-red.md` para comandos de acceso.
- La API es el único servicio público. Se accede vía Tailscale Funnel: `https://debian-server.taile532c7.ts.net/api`
- El firewall está documentado en `05-red.md#firewall-docker-user`.
