# Desarrollo de endpoints (API FastAPI)

Guía corta para agregar endpoints a `compose/api/app/` siguiendo el contrato actual. Referencia: `GET /api/resources`.

## Estructura

| Archivo | Rol |
|---------|-----|
| `routers/public.py` | Solo `GET /api/health`; sin autenticación |
| `routers/private.py` | Todos los demás endpoints; hereda `X-API-Key` |
| `config.py` | `API_KEY`, comparación constant-time y fail-closed |
| `power.py` | Aprobación y cliente del socket de apagado |
| `util.py` | `verify_key`, `HOSTNAME`, servicios y socket-proxy de Docker |
| `main.py` | App, versión, lifespan y `/openapi.json` protegido |

## Reglas

1. **Privado por defecto.** Si no es estrictamente público, va en `private.py`; el router ya aplica `Depends(verify_key)`. Solo `health` debe quedar público.
2. **Sin dependencias nuevas** salvo que sea imprescindible. Preferir `os`, `shutil`, `glob`, `time` y lectura de `/proc`.
3. **Nunca** montar `docker.sock` ni ampliar permisos. Para datos de Docker, usar `socket-proxy` (hoy solo `GET /containers/json`).
4. **Contrato JSON plano**: incluir `timestamp` ISO UTC y `hostname` cuando aplique. Para bodies, Pydantic con `extra="forbid"` y `Field(...)`.
5. **Degradación elegante**: si falla una lectura, devolver `null` en ese campo; no responder 500.
6. **No bloquear el event loop**: usar `def` sync (FastAPI lo ejecuta en threadpool) para lectura de archivos y esperas cortas, o `async` + `asyncio.to_thread` si hay I/O real.
7. **No loguear secretos**. Si se agregan headers/query sensibles, sumarlos a `SENSITIVE_HEADERS` / `SENSITIVE_QUERY_PARAMS`.

## Ejemplo: `/api/resources`

- Helpers en `routers/private.py`: CPU, load, memoria/swap, disco, uptime y temperatura.
- CPU: dos lecturas de `/proc/stat` separadas 100 ms; `usage = 100 * (1 - idle_delta / total_delta)`.
- Memoria: `/proc/meminfo`; `used = total - available`.
- Disco: `shutil.disk_usage(path)`; deduplicar por `st_dev`.
- Temperatura: leer `/sys/class/thermal/thermal_zone*/temp`; **omitir el campo** si no existe.
- Ojo: `def time()` ya existe en `private.py` y sombrea el módulo `time`. Usar `from time import sleep` o `import time as time_module`.

Qué miden las métricas desde el contenedor:

- `/proc/stat`, `/proc/loadavg`, `/proc/meminfo` y `/proc/uptime` **no están namespaced**: reflejan el host.
- `shutil.disk_usage("/")` solo ve el filesystem montado en el contenedor (overlay). Para el disco real del host hace falta un bind mount de solo lectura puntual, con confirmación explícita.

## Checklist al agregar un endpoint

1. Implementarlo en `routers/private.py` (o `public.py` solo si es realmente público).
2. Actualizar los listados hardcodeados de `GET /` (`endpoints`) y `GET /api` (`private_endpoints`).
3. Subir la versión en `main.py` (y en las respuestas de `/` y `/api`).
4. Documentar en `docs/api.md`, agregar la request a la colección Postman y anotar el cambio en `CHANGELOG.md`.
5. Validar: `python3 -m compileall -q compose/api/app` y `docker compose config` con ambos archivos.
6. Actualizar el tag de imagen en `compose/api/compose.yaml`.
7. Reconstruir y desplegar **siempre** con el override de Funnel:

```bash
cd compose/api
docker compose -f compose.yaml -f compose.funnel-transition.yaml build
docker compose -f compose.yaml -f compose.funnel-transition.yaml up -d
```

8. Verificar: contenedor `healthy`; `GET /api/health` 200; endpoint nuevo 401 sin key y 200 con key; Funnel sigue respondiendo.

Para probar con la key sin imprimirla:

```bash
docker exec api python -c "
import os, json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8000/api/resources',
                             headers={'X-API-Key': os.environ['API_KEY']})
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
"
```
