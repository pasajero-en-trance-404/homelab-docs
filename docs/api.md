# Homelab API

## Descripción general

API pública del homelab, construida con FastAPI (Python). Expone endpoints públicos de utilidad (health, hora, IP, UUID) y endpoints privados de administración protegidos con `X-API-Key`.

Accesible públicamente por Tailscale Funnel y localmente por Traefik:

- **Público (Funnel)**: `https://debian-server.taile532c7.ts.net/api`
- **Local (Traefik)**: `http://api.homelab` (via `127.0.0.1:80` con `Host: api.homelab`)
- **Local (directo)**: `http://127.0.0.1:8000`

La documentación interactiva (Swagger UI) está disponible en `/docs` y el schema OpenAPI en `/openapi.json`.

### Especificación

| Aspecto | Valor |
|---------|-------|
| Versión | 1.0.0 |
| Formato | JSON |
| Autenticación | Header `X-API-Key` (solo endpoints privados) |
| Servidor | Container `api` (red `homelab`) |
| Código | `compose/api/app/` |

## Autenticación X-API-Key

Los endpoints privados requieren el header `X-API-Key` con la key configurada en `compose/api/.env` (`API_KEY`).

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api/status
```

- **Sin header** o **key inválida** → `401 {"detail":"Invalid API Key"}`
- La key se genera con `openssl rand -hex 32` y nunca se commitea (`.env` está en `.gitignore`)
- Los endpoints públicos **no requieren** key

## Endpoints públicos

Sin autenticación.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Landing: nombre, versión y lista de endpoints |
| `GET` | `/api/health` | Liveness check (estado del servicio) |
| `GET` | `/api/time` | Hora del servidor en UTC + timestamp Unix |
| `GET` | `/api/ip` | IP del cliente vista por el servidor |
| `GET` | `/api/request` | Echo sanitizado de la request (sin headers sensibles) |
| `GET` | `/api/server` | Hostname y uptime del servidor (datos mínimos) |
| `GET` | `/api/uuid` | UUID v4 aleatorio |
| `GET` | `/docs` | Documentación automática (Swagger UI) |
| `GET` | `/openapi.json` | Schema OpenAPI de la API |

### `GET /`

```bash
curl http://127.0.0.1:8000/
```

```json
{
  "name": "Homelab API",
  "version": "1.0.0",
  "description": "API pública del homelab",
  "endpoints": {
    "root": "/",
    "health": "/api/health",
    "time": "/api/time",
    "ip": "/api/ip",
    "request": "/api/request",
    "server": "/api/server",
    "uuid": "/api/uuid",
    "docs": "/docs"
  },
  "timestamp": "2026-07-31T02:20:22.927652+00:00"
}
```

### `GET /api/health`

```bash
curl http://127.0.0.1:8000/api/health
```

```json
{
  "status": "ok",
  "server": "debian-server",
  "timestamp": "2026-07-31T02:20:23.029154+00:00"
}
```

### `GET /api/time`

```bash
curl http://127.0.0.1:8000/api/time
```

```json
{
  "time_utc": "2026-07-31T02:20:23.080389+00:00",
  "unix_seconds": 1785464423,
  "timezone": "UTC",
  "server": "debian-server"
}
```

### `GET /api/ip`

```bash
curl http://127.0.0.1:8000/api/ip
```

```json
{
  "ip": "172.22.0.1",
  "source": "direct"
}
```

Con `X-Forwarded-For` (por ejemplo, detrás de un proxy), `source` será `x-forwarded-for` y `ip` el primer valor del header.

### `GET /api/request`

```bash
curl -H "User-Agent: curl/8.0" "http://127.0.0.1:8000/api/request?foo=bar"
```

```json
{
  "method": "GET",
  "path": "/api/request",
  "query": {"foo": "bar"},
  "user_agent": "curl/8.0",
  "referer": null,
  "headers": {
    "host": "127.0.0.1:8000",
    "accept": "*/*",
    "user-agent": "curl/8.0"
  }
}
```

Los headers sensibles (`Authorization`, `Proxy-Authorization`, `X-API-Key`, `Cookie`, `Set-Cookie`) se filtran y no aparecen en la respuesta.

### `GET /api/server`

```bash
curl http://127.0.0.1:8000/api/server
```

```json
{
  "hostname": "debian-server",
  "uptime_seconds": 22180,
  "timestamp": "2026-07-31T02:20:23.233038+00:00"
}
```

### `GET /api/uuid`

```bash
curl http://127.0.0.1:8000/api/uuid
```

```json
{
  "uuid": "b8b584c4-865f-4a7f-8b52-63ac4bf23783",
  "version": 4,
  "timestamp": "2026-07-31T02:20:23.308270+00:00"
}
```

## Endpoints privados

Requieren el header `X-API-Key`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api` | Resumen del estado de la API |
| `GET` | `/api/status` | Estado de los contenedores (up/down/unknown) |
| `GET` | `/api/containers` | Detalle de contenedores (imagen, estado, health) |

### `GET /api`

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api
```

```json
{
  "service": "homelab-api",
  "status": "running",
  "version": "1.0.0",
  "private_endpoints": ["/api/status", "/api/containers"]
}
```

### `GET /api/status`

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api/status
```

```json
{
  "server": "debian-server",
  "services": {
    "traefik": "up",
    "homepage": "up",
    "portainer": "up",
    "n8n": "up",
    "uptime-kuma": "up"
  },
  "timestamp": "2026-07-31T02:20:23.449788+00:00"
}
```

### `GET /api/containers`

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api/containers
```

```json
{
  "server": "debian-server",
  "containers": [
    {
      "name": "api",
      "image": "api-api",
      "state": "running",
      "status": "Up 26 minutes"
    },
    {
      "name": "traefik",
      "image": "traefik:latest",
      "state": "running",
      "status": "Up 2 hours"
    }
  ],
  "timestamp": "2026-07-31T02:20:23.449788+00:00"
}
```

### Respuesta de error (401)

Sin key o con key inválida:

```bash
curl -i http://127.0.0.1:8000/api/status
```

```
HTTP/1.1 401 Unauthorized
content-type: application/json

{"detail":"Invalid API Key"}
```

## Consideraciones de seguridad

- **Funnel expone la API a todo Internet** — los endpoints públicos no tienen autenticación
- La API key (`API_KEY`) vive en `compose/api/.env`, fuera de git y excluida de los backups
- `/api/server` expone solo hostname y uptime (sin versión de Docker/Python, sin disco, sin conteo de contenedores) — evita fingerprinting
- `/api/request` filtra headers sensibles (`Authorization`, `X-API-Key`, `Cookie`, `Proxy-Authorization`)
- `/api/ip` expone la IP del cliente, nunca IPs internas del servidor
- `/api/status` y `/api/containers` consultan el socket de Docker (montado en modo **read-only**) — solo accesibles con key válida
- No exponer paneles administrativos por Funnel; la API es el único servicio público
- Funnel no incluye WAF ni rate limiting — capa futura con reverse proxy + TLS
- Rotar la key con `openssl rand -hex 32` si se sospecha filtración

## Rotación de API Key

```bash
# Generar nueva key
openssl rand -hex 32

# Actualizar en compose/api/.env
API_KEY=nueva-key-generada

# Reiniciar el contenedor
docker compose -f compose/api/compose.yaml up -d
```

## Colección Postman

Hay una colección importable en `docs/postman/homelab-api.postman_collection.json` con todos los endpoints, casos 401 y variables `{{base_url}}` y `{{api_key}}`.

## Referencias

- Código: `compose/api/app/`
- Acceso público: `docs/public-access.md`
- Arquitectura: `docs/architecture.md`
