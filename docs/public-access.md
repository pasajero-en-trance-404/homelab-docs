# Acceso público — Tailscale Funnel

## Resumen

Este documento describe cómo se expone la API del homelab a Internet de forma segura usando **Tailscale Funnel**, sin abrir puertos en el router ni exponer la IP pública del servidor.

## Arquitectura

```
Usuario externo
    |
    | https://debian-server.taile532c7.ts.net/api
    |
    ▼
Tailscale Funnel (TLS automático Let's Encrypt)
    |
    | Tráfico enrutado por DERP relay → WireGuard
    |
    ▼
Servidor Debian (192.168.1.50)
    |
    | localhost:8000
    |
    ▼
Docker — container api:8000 (red homelab)
    |
    ▼
FastAPI — GET /api, GET /api/health, GET /api/status
```

### Flujo de tráfico

1. El usuario accede a `https://debian-server.taile532c7.ts.net/api`
2. Tailscale Funnel recibe la conexión en un DERP relay (infraestructura de Tailscale)
3. El relay reenvía el tráfico cifrado por WireGuard al servidor
4. El demonio `tailscaled` recibe y proxy localmente a `127.0.0.1:8000`
5. Docker responde desde el contenedor `api`

No hay puertos abiertos en el router. No hay IP pública expuesta. TLS es automático (Let's Encrypt vía Tailscale).

## Tailscale Serve vs Funnel

| Característica | Serve | Funnel |
|----------------|-------|--------|
| Alcance | Solo tailnet (tus dispositivos) | Internet público |
| Autenticación | Sí (identidad Tailscale) | No (público) |
| URL | `https://host.tailnet.ts.net` | `https://host.tailnet.ts.net` |
| Caso de uso | Paneles de admin, monitoreo | APIs públicas, webhooks |

### Regla general

**Funnel solo para la API.** Todo panel administrativo (Portainer, Homepage, n8n, Uptime Kuma) se accede directamente por Tailscale usando la IP del tailnet o por LAN, sin Serve ni Funnel.

## Servicios: públicos vs privados

### Público (Tailscale Funnel)

| Servicio | URL | Puerto local |
|----------|-----|--------------|
| API | `https://debian-server.taile532c7.ts.net/api` | 8000 |

### Privado (solo Tailscale / LAN)

| Servicio | Acceso | Puerto |
|----------|--------|--------|
| Homepage | tailnet + LAN (192.168.1.0/24) | 3000 |
| Portainer | solo tailnet | 9000 |
| n8n | solo tailnet | 5678 |
| Uptime Kuma | solo tailnet | 3001 |

Los servicios privados se acceden directamente por `http://debian-server:<puerto>` desde la tailnet (Tailscale resuelve el hostname automáticamente).

## Comandos de referencia

### Activar Funnel para la API

```bash
sudo tailscale funnel --bg 8000
```

### Desactivar Funnel

```bash
sudo tailscale funnel --https=443 off
```

### Verificar estado

```bash
tailscale funnel status
```

### Acceder a servicios privados por Tailscale

No se necesita Serve. Los servicios son accesibles directamente desde la tailnet:

```bash
# Desde cualquier dispositivo conectado a Tailscale
http://debian-server:3000   # Homepage
http://debian-server:9000   # Portainer
http://debian-server:5678   # n8n
http://debian-server:3001   # Uptime Kuma
```

### Desactivar Serve

```bash
sudo tailscale serve --https=443 off
```

## Puesta en producción

Comandos usados para exponer la API:

```bash
# 1. Resetear configuración previa
sudo tailscale funnel reset

# 2. Exponer API públicamente por Funnel
sudo tailscale funnel --bg 8000
```

La API responde en:
- `https://debian-server.taile532c7.ts.net/api`
- `https://debian-server.taile532c7.ts.net/api/health`

Los servicios administrativos se acceden por Tailscale directo sin Serve/Funnel.

## DuckDNS

El dominio `homelab404-debian.duckdns.org` está registrado para uso futuro.

Actualmente no es posible vincular DuckDNS directamente a Tailscale Funnel porque:
- DuckDNS solo admite registros A/AAAA (IPs)
- Funnel no expone una IP pública fija, usa la infraestructura de Tailscale

**Uso futuro posible:**
- Reverse proxy (Traefik / Nginx Proxy Manager)
- Cloudflare Tunnel
- Redirección desde el dominio DuckDNS hacia la URL de Funnel

## Seguridad

### API Key

La API soporta el header `X-API-Key` para endpoints protegidos.

Los endpoints públicos actuales no requieren key:
- `GET /api/health`

Los endpoints protegidos requieren `X-API-Key`:
- `GET /api`
- `GET /api/status`

Para agregar protección a un endpoint futuro:

```python
@app.get("/api/protegido")
def protegido(_=Depends(verify_key)):
    ...
```

### Rotación de API Key

```bash
# Generar nueva key
openssl rand -hex 32

# Actualizar en compose/api/.env
API_KEY=nueva-key-generada

# Reiniciar el contenedor
docker compose -f compose/api/compose.yaml up -d
```

### Riesgos

- **Funnel expone el servicio a todo Internet** — no hay autenticación de Tailscale
- No exponer paneles administrativos por Funnel
- Mantener la API key fuera de git (`.env` está en `.gitignore`)
- Montar `/var/run/docker.sock` (read-only) da acceso de lectura a la API de Docker — no exponer datos crudos
- Monitorear logs del contenedor ante actividad sospechosa
- Considerar rate limiting si el servicio recibe tráfico no deseado
- Funnel no incluye WAF (Web Application Firewall) — eso sería una capa futura con reverse proxy

## Referencias

- [Tailscale Funnel docs](https://tailscale.com/kb/1223/tailscale-funnel)
- [Tailscale Serve docs](https://tailscale.com/kb/1242/tailscale-serve)
