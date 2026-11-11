# Análisis del server (verificado contra el contenedor en ejecución)

## 1. Qué es
Debian 13 + Docker. La API es FastAPI 0.162 / Python 3.12, corre como usuario no-root 10001, en compose/api/app/, detrás de Tailscale Funnel (https://debian-server.taile532c7.ts.net → 127.0.0.1:8000) y de Traefik en LAN (https://debian-server.local). Estado: healthy, ~1.8 GB RAM en uso de 3.1 GB.

## 2. Endpoints reales (openapi en vivo)
| Método | Ruta | Auth | Implementado en |
|---|---|---|---|
| GET | /api/health | Pública (única) | routers/public.py:6 |
| GET | / | X-API-Key | routers/private.py:52 |
| GET | /api | X-API-Key | routers/private.py:72 |
| GET | /api/status | X-API-Key | routers/private.py:82 |
| GET | /api/containers | X-API-Key | routers/private.py:101 |
| GET | /api/time | X-API-Key | routers/private.py:110 |
| GET | /api/ip | X-API-Key | routers/private.py:121 |
| GET | /api/request | X-API-Key | routers/private.py:129 |
| GET | /api/server | X-API-Key | routers/private.py:148 |
| GET | /api/uuid | X-API-Key | routers/private.py:162 |
| POST | /api/power/shutdown/prepare | X-Power-Approval-Key + X-API-Key | routers/private.py:171 |
| POST | /api/power/shutdown | X-Power-Approval-Key + X-API-Key | routers/private.py:191 |
| GET | /openapi.json | X-API-Key | main.py:36 |

/docs y /redoc están deshabilitados (docs_url=None). Verificado: /, /api/time, /api/server, /api/status devuelven 401 sin key; solo /api/health da 200.

## 3. Arquitectura general
- Internet → Tailscale Funnel → 127.0.0.1:8000 → contenedor api
- LAN → Traefik :443 (TLS) debian-server.local → api:8000
- LAN → Traefik :80 *.homelab → homepage/portainer/n8n/uptime
- Red externa homelab (172.22.0.0/16) para todos los servicios.
- Red interna homelab-docker-api: la API no monta docker.sock; habla con socket-proxy (solo GET /containers/json). Ver compose.yaml.
- Power: la API escribe a un socket Unix /run/homelab-power/poweroff.sock, atendido por systemd como root (host-power/), con token de aprobación de 30 s, un solo shutdown pendiente y auditoría sin secretos (power.py).
- Auth: X-API-Key se compara con SHA-256 + hmac.compare_digest; la app falla al arrancar si API_KEY falta (config.py:20).
- Firewall DOCKER-USER: permite Tailscale, salida DNS/HTTP/ICMP de contenedores, LAN solo a 3000 y 443; el resto DROP. Puertos admin expuestos en 0.0.0.0 (3000/3001/5678/9000) pero bloqueados por firewall.
- Volúmenes de datos: ~/homelab-data/; compose y config en ~/homelab-docs/; secretos fuera de git.

## 4. Qué tener en cuenta para agregar un endpoint
1. ¿Público o privado? Todo en routers/private.py hereda X-API-Key (private.py:21). Si es público va en public.py; Funnel lo expone a Internet sin WAF ni rate limiting.
2. Rebuild obligatorio: el código se copia en la imagen (COPY app/ /app), no hay bind mount. Hay que `docker compose build` + `up -d`.
3. Cuidado al desplegar: el contenedor corre con compose.yaml + compose.funnel-transition.yaml (el override publica 127.0.0.1:8000). Si se hace `up -d` solo con compose.yaml, se cae Funnel. Incluir ambos -f.
4. Contrato de respuesta: seguir la convención existente (timestamp ISO UTC, HOSTNAME, JSON plano). Para bodies usar Pydantic con extra="forbid" y Field(...) como en ShutdownApprovalRequest.
5. Seguridad: no loguear secretos; si se agregan headers/query sensibles, sumarlos a SENSITIVE_HEADERS/SENSITIVE_QUERY_PARAMS (private.py). Nunca montar docker.sock; si hacen falta más datos de Docker, ampliar el allowlist de socket-proxy (y recrearlo).
6. Metadatos desactualizados: GET / tiene endpoints y /api tiene private_endpoints hardcodeados y no listan power. También la versión en main.py (1.0.0).
7. Sin tests ni lint en el repo (solo .dockerignore excluye tests/). Validar con `docker compose config` y `python -m compileall`.
8. Docs desactualizadas: docs/api.md, public-access.md, README.md y AGENTS.md dicen que /, /api/time, /api/ip, /api/request, /api/server, /api/uuid son públicos y que existe /docs. En el código no es así (todo privado salvo health, /docs deshabilitado).
9. Imagen/tag fijado a stage7-power-audit-20261107; si no se reemplaza con --build, Docker puede reutilizar la imagen vieja.
10. Recursos limitados (3 GB RAM): evitar operaciones pesadas o bloqueantes; los handlers sync de FastAPI van al threadpool, los async no.
