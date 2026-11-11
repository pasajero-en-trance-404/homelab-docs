# Homelab API

## Descripción general

API del homelab, construida con FastAPI (Python). La única ruta sin autenticación es `GET /api/health`; el resto requiere `X-API-Key`. Los endpoints de apagado usan además `X-Power-Approval-Key`.

Accesible públicamente por Tailscale Funnel y localmente por Traefik:

- **Público (Funnel)**: `https://debian-server.taile532c7.ts.net`
- **LAN (Traefik + TLS)**: `https://debian-server.local`
- **Local (directo)**: `http://127.0.0.1:8000`

La documentación interactiva (Swagger UI y ReDoc) está **deshabilitada** (`/docs` y `/redoc` no existen). El schema OpenAPI está disponible en `/openapi.json`, protegido con `X-API-Key` como el resto de las rutas privadas.

### Especificación

| Aspecto | Valor |
|---------|-------|
| Versión | 1.1.0 |
| Formato | JSON |
| Autenticación | Header `X-API-Key` (todo excepto `/api/health`) |
| Servidor | Container `api` (redes `homelab` y `homelab-docker-api`) |
| Código | `compose/api/app/` |

## Autenticación X-API-Key

Los endpoints privados requieren el header `X-API-Key` con la key configurada en `compose/api/.env` (`API_KEY`).

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api/status
```

- **Sin header** o **key inválida** → `401 {"detail":"Invalid API Key"}`
- La comparación es constant-time (SHA-256 + `hmac.compare_digest`)
- La app **no arranca** si `API_KEY` falta o está vacía
- La key se genera con `openssl rand -hex 32` y nunca se commitea (`.env` está en `.gitignore`)
- Solo `/api/health` es público

## Endpoints públicos

Sin autenticación.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/health` | Liveness check (payload mínimo) |

### `GET /api/health`

```bash
curl http://127.0.0.1:8000/api/health
```

```json
{"status": "ok"}
```

## Endpoints privados

Requieren el header `X-API-Key`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Landing: nombre, versión y lista de endpoints |
| `GET` | `/api` | Resumen del estado de la API |
| `GET` | `/api/status` | Estado de los contenedores (up/down/unknown) |
| `GET` | `/api/containers` | Detalle de contenedores (imagen, estado, health) |
| `GET` | `/api/time` | Hora del servidor en UTC + timestamp Unix |
| `GET` | `/api/ip` | IP del cliente vista por el servidor |
| `GET` | `/api/request` | Echo sanitizado de la request |
| `GET` | `/api/server` | Hostname y uptime del servidor |
| `GET` | `/api/uuid` | UUID v4 aleatorio |
| `GET` | `/api/resources` | CPU, memoria, disco y uptime (métricas del host/contenedor) |
| `POST` | `/api/power/shutdown/prepare` | Emite una aprobación de apagado (30 s) |
| `POST` | `/api/power/shutdown` | Consume la aprobación y apaga el host |
| `GET` | `/openapi.json` | Schema OpenAPI de la API |

### `GET /`

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/
```

```json
{
  "name": "Homelab API",
  "version": "1.1.0",
  "description": "API del homelab",
  "endpoints": {
    "root": "/",
    "health": "/api/health",
    "status": "/api/status",
    "containers": "/api/containers",
    "time": "/api/time",
    "ip": "/api/ip",
    "request": "/api/request",
    "server": "/api/server",
    "uuid": "/api/uuid",
    "resources": "/api/resources",
    "power_shutdown_prepare": "/api/power/shutdown/prepare",
    "power_shutdown": "/api/power/shutdown",
    "openapi": "/openapi.json"
  },
  "timestamp": "2026-11-10T22:20:22.927652+00:00"
}
```

### `GET /api`

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api
```

```json
{
  "service": "homelab-api",
  "status": "running",
  "version": "1.1.0",
  "private_endpoints": [
    "/",
    "/api",
    "/api/status",
    "/api/containers",
    "/api/time",
    "/api/ip",
    "/api/request",
    "/api/server",
    "/api/uuid",
    "/api/resources",
    "/api/power/shutdown/prepare",
    "/api/power/shutdown",
    "/openapi.json"
  ]
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
      "image": "homelab-ai-api:v1.1.0-resources-20261110",
      "state": "running",
      "status": "Up 26 minutes"
    }
  ],
  "timestamp": "2026-07-31T02:20:23.449788+00:00"
}
```

### `GET /api/time`

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api/time
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
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api/ip
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
curl -H "X-API-Key: <tu-key>" -H "User-Agent: curl/8.0" \
  "http://127.0.0.1:8000/api/request?foo=bar"
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

Los headers sensibles (`Authorization`, `Proxy-Authorization`, `X-API-Key`, `X-Power-Approval-Key`, `Cookie`, `Set-Cookie`) se filtran. También se redactan query params sensibles (`api_key`, `token`, `password`, `secret`, `approval_token`, etc.).

### `GET /api/server`

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api/server
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
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api/uuid
```

```json
{
  "uuid": "b8b584c4-865f-4a7f-8b52-63ac4bf23783",
  "version": 4,
  "timestamp": "2026-07-31T02:20:23.308270+00:00"
}
```

### `GET /api/resources`

```bash
curl -H "X-API-Key: <tu-key>" http://127.0.0.1:8000/api/resources
```

```json
{
  "hostname": "debian-server",
  "timestamp": "2026-11-11T01:24:05.152624+00:00",
  "uptime_seconds": 38316,
  "cpu": {
    "cores": 2,
    "load_average": {"1m": 0.08, "5m": 0.17, "15m": 0.17},
    "usage_percent": 5.0
  },
  "memory": {
    "total_bytes": 3259953152,
    "used_bytes": 2081710080,
    "available_bytes": 1178243072,
    "used_percent": 63.86,
    "swap": {
      "total_bytes": 2147479552,
      "used_bytes": 524288,
      "free_bytes": 2146955264,
      "used_percent": 0.02
    }
  },
  "disk": [
    {
      "path": "/",
      "total_bytes": 63871643648,
      "used_bytes": 13855703040,
      "free_bytes": 46738251776,
      "used_percent": 21.69
    }
  ]
}
```

Notas sobre lo que mide cada campo **desde dentro del contenedor**:

- `cpu.cores`: núcleos visibles (`os.cpu_count()`, normalmente los del host).
- `cpu.load_average`: `/proc/loadavg`, que **no está namespaced**: refleja el host.
- `cpu.usage_percent`: delta de dos lecturas de `/proc/stat` separadas 100 ms; también refleja el host. Es aproximado y puede devolver `null` si no hay delta.
- `memory`: `/proc/meminfo` refleja la **memoria del host**, no un límite de cgroup. `used = total - available`.
- `disk`: `shutil.disk_usage()` solo ve los filesystems **montados en el contenedor** (`/` es el overlay de la imagen, `/app` comparte el mismo device y se deduplica). Para ver el disco real del host haría falta un bind mount de solo lectura (no aplicado).
- `temperature_c`: solo aparece si `/sys/class/thermal/thermal_zone*/temp` está disponible; si no, el campo se omite.
- Cualquier lectura fallida devuelve `null` en ese campo, sin responder 500.

### `POST /api/power/shutdown/prepare`

Requiere `X-API-Key` **y** `X-Power-Approval-Key` (variable `POWER_API_KEY`). Emite un `approval_token` de un solo uso, válido 30 s, para la operación fija `host.shutdown`.

```bash
curl -X POST -H "X-API-Key: <tu-key>" -H "X-Power-Approval-Key: <power-key>" \
  http://127.0.0.1:8000/api/power/shutdown/prepare
```

```json
{
  "operation": "host.shutdown",
  "approval_token": "<token>",
  "expires_at": "2026-11-10T22:20:53.308270+00:00"
}
```

- `201` si se emitió la aprobación.
- `409` si ya hay una operación pendiente.

### `POST /api/power/shutdown`

Consume la aprobación y envía la acción fija al socket Unix del host. No acepta parámetros distintos de `approval_token`.

```bash
curl -X POST -H "X-API-Key: <tu-key>" -H "X-Power-Approval-Key: <power-key>" \
  -H "Content-Type: application/json" \
  -d '{"approval_token":"<token>"}' \
  http://127.0.0.1:8000/api/power/shutdown
```

```json
{
  "status": "shutdown_scheduled",
  "operation": "host.shutdown",
  "audit_id": "<32 hex>"
}
```

- `202` si el helper aceptó el apagado.
- `409` si el token es inválido, expiró, ya se usó o hay uno pendiente.
- `503` si el helper no está disponible o el resultado es desconocido.

La auditoría usa `power_event=... operation=host.shutdown audit_id=<32 hex>` y nunca registra las keys ni el token.

### Respuesta de error (401)

Sin key o con key inválida:

```bash
curl -i http://127.0.0.1:8000/api/status
```

```
HTTP/1.1 401 Unauthorized
content-type: application/json
www-authenticate: X-API-Key

{"detail":"Invalid API Key"}
```

## Consideraciones de seguridad

- **Funnel expone la API a todo Internet**, pero solo `/api/health` responde sin autenticación
- La API key (`API_KEY`) y la de power (`POWER_API_KEY`) viven en `compose/api/.env`, fuera de git y excluidas de los backups
- La API **no monta `/var/run/docker.sock`**: consulta un `socket-proxy` interno de solo lectura que únicamente permite `GET /containers/json`
- `/api/resources` revela métricas del host (CPU, memoria, uptime, disco del contenedor); mantenerlo privado
- `/api/request` filtra headers y query params sensibles
- `/api/ip` expone la IP del cliente, nunca IPs internas del servidor
- Los endpoints de power requieren dos headers, token de un solo uso y un helper systemd restringido
- No exponer paneles administrativos por Funnel; la API es el único servicio público
- Funnel no incluye WAF ni rate limiting — capa futura con reverse proxy + TLS
- Rotar las keys con `openssl rand -hex 32` si se sospecha filtración

## Rotación de API Key

```bash
# Generar nueva key
openssl rand -hex 32

# Actualizar en compose/api/.env
API_KEY=nueva-key-generada

# Reconstruir/reiniciar (siempre con ambos archivos)
docker compose -f compose/api/compose.yaml \
  -f compose/api/compose.funnel-transition.yaml up -d
```

## Colección Postman

Hay una colección importable en `docs/postman/homelab-api.postman_collection.json` con endpoints, casos 401 y variables `{{base_url}}` y `{{api_key}}`.

## Referencias

- Código: `compose/api/app/`
- Acceso público: `docs/public-access.md`
- Arquitectura: `docs/architecture.md`
- Análisis del server: `docs/ANALISIS-SERVER.md`
