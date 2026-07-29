# Servicios instalados

## Plataforma

- Docker Engine: 29.6.2
- Docker Compose: v5.3.1
- Red compartida: `homelab` (external bridge, 172.22.0.0/16)

## Servicios

| Servicio    | Imagen                                    | Puerto  | Estado               | Red      | Ruta de datos                             |
|-------------|-------------------------------------------|---------|----------------------|----------|--------------------------------------------|
| Portainer   | portainer/portainer-ce:latest             | 9000    | Up                   | homelab  | ~/homelab-data/portainer                   |
| Homepage    | ghcr.io/gethomepage/homepage:latest       | 3000    | Up (healthy)         | homelab  | ~/homelab-data/homepage                    |
| n8n         | docker.n8n.io/n8nio/n8n:latest            | 5678    | Up                   | homelab  | ~/homelab-data/n8n                         |
| Uptime Kuma | louislam/uptime-kuma:latest               | 3001    | Up (healthy)         | homelab  | ~/homelab-data/uptime-kuma                 |

## Puertos utilizados

| Puerto | Servicio    | Uso                |
|--------|-------------|--------------------|
| 22     | SSH         | Acceso remoto      |
| 3000   | Homepage    | Dashboard          |
| 3001   | Uptime Kuma | Monitoreo de uptime|
| 5678   | n8n         | Automatización     |
| 9000   | Portainer   | Admin. contenedores|

## Red

- Interfaz: enp3s0
- IP: 192.168.1.50/24
- Gateway: 192.168.1.1
- DNS: 192.168.1.1, 1.1.1.1

## Notas

- Portainer, Uptime Kuma y Homepage exponen el puerto del host mapeado 1:1.
- n8n usa la variable `${N8N_PORT}` definida en `compose/n8n/.env`.
- No hay reverse proxy ni SSL configurado. Todos los servicios acceden por HTTP.
- Homepage tiene acceso al socket de Docker para mostrar contenedores en el dashboard.
