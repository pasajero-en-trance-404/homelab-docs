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
FastAPI — GET /api, GET /api/health
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

**Funnel solo para la API.** Todo panel administrativo (Portainer, Homepage, n8n, Uptime Kuma) debe usar **Serve** para mantenerse privado dentro del tailnet.

## Servicios: públicos vs privados

### Público (Tailscale Funnel)

| Servicio | URL | Puerto local |
|----------|-----|--------------|
| API | `https://debian-server.taile532c7.ts.net/api` | 8000 |

### Privado (Tailscale Serve / LAN)

| Servicio | Acceso | Puerto |
|----------|--------|--------|
| Homepage | tailnet + LAN (192.168.1.0/24) | 3000 |
| Portainer | solo tailnet | 9000 |
| n8n | solo tailnet | 5678 |
| Uptime Kuma | solo tailnet | 3001 |

## Comandos de referencia

### Activar Funnel para la API

```bash
sudo tailscale funnel --bg 8000
```

### Desactivar Funnel

```bash
sudo tailscale funnel 8000 off
```

### Verificar estado

```bash
tailscale funnel status
```

### Activar Serve para servicios privados (ej: Homepage)

```bash
sudo tailscale serve --bg 3000
```

### Desactivar Serve

```bash
sudo tailscale serve 3000 off
```

## Migrar Funnel de Homepage a API

Si tenés Funnel activo en el puerto 3000 (Homepage) y querés que la API esté en la raíz:

```bash
# 1. Desactivar Funnel en Homepage
sudo tailscale funnel 3000 off

# 2. Activar Funnel para la API
sudo tailscale funnel --bg 8000

# 3. (Opcional) Homepage disponible solo por Tailscale Serve
sudo tailscale serve --bg 3000
```

Luego la API responde en:
- `https://debian-server.taile532c7.ts.net/api`
- `https://debian-server.taile532c7.ts.net/api/health`

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
- `GET /api`
- `GET /api/health`

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
- Monitorear logs del contenedor ante actividad sospechosa
- Considerar rate limiting si el servicio recibe tráfico no deseado
- Funnel no incluye WAF (Web Application Firewall) — eso sería una capa futura con reverse proxy

## Referencias

- [Tailscale Funnel docs](https://tailscale.com/kb/1223/tailscale-funnel)
- [Tailscale Serve docs](https://tailscale.com/kb/1242/tailscale-serve)
