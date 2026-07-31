# Traefik — Reverse Proxy

## Arquitectura

Traefik actúa como punto de entrada único para todos los servicios Docker del homelab, enrutando por nombre de host (host-based routing).

```
Cliente
  │
  │ http://<servicio>.homelab:80
  │
  ▼
Traefik (127.0.0.1:80)
  │
  │ Docker provider — labels en cada contenedor
  │
  ├── api.homelab      ──→ api:8000
  ├── homepage.homelab  ──→ homepage:3000
  ├── portainer.homelab ──→ portainer:9000
  ├── n8n.homelab       ──→ n8n:5678
  └── uptime.homelab    ──→ uptime-kuma:3001
```

### Entrypoints

| Entrypoint | Puerto | Binding | Uso |
|------------|--------|---------|-----|
| `web` | 80 | `127.0.0.1:80` | HTTP — todos los servicios |
| Dashboard | 8080 | `127.0.0.1:8080` | Panel interno de Traefik |

Ambos entrypoints bindean solo a `localhost`. No hay exposición a LAN ni a Internet. El acceso externo se realiza exclusivamente por Tailscale (directo a puertos) o Tailscale Funnel (solo API).

### Providers

| Provider | Modo | Detalle |
|----------|------|---------|
| Docker | Dinámico | Lee labels de contenedores en el socket Docker |
| Archivo | Estático | `traefik.yml` montado como bind mount `:ro` |

`exposedByDefault: false` — solo los contenedores con `traefik.enable=true` son ruteados.

## Funcionamiento

### Host-based routing

Cada servicio se identifica por el header `Host` de la petición HTTP:

```
Host: homepage.homelab  →  router "homepage"  →  contenedor homepage:3000
Host: api.homelab       →  router "api"       →  contenedor api:8000
```

Los hostnames `*.homelab` son locales. Para usarlos desde un navegador, se debe agregar una entrada en `/etc/hosts` del cliente:

```
# Linux / macOS
100.119.176.84 homepage.homelab api.homelab portainer.homelab n8n.homelab uptime.homelab traefik.homelab
```

O desde la línea de comandos para pruebas rápidas:

```bash
curl -H "Host: homepage.homelab" http://127.0.0.1
curl -H "Host: api.homelab" http://127.0.0.1/api/health
```

### Dashboard

Accesible en `http://traefik.homelab:8080` (o `curl -H "Host: traefik.homelab" http://127.0.0.1:8080`).

El dashboard muestra:
- Routers configurados y su estado
- Servicios detectados por Docker provider
- Configuración actual en tiempo real

## Integración con Docker

### Convención de labels

Cada servicio expuesto por Traefik debe tener estos labels en su `compose.yaml`:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.<nombre>.rule=Host(`<nombre>.homelab`)"
  - "traefik.http.routers.<nombre>.entrypoints=web"
  - "traefik.http.services.<nombre>.loadbalancer.server.port=<puerto>"
```

Donde `<nombre>` es un identificador único (ej: `api`, `homepage`, `portainer`) y `<puerto>` es el puerto interno del contenedor.

### Dashboard

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.dashboard.rule=Host(`traefik.homelab`)"
  - "traefik.http.routers.dashboard.entrypoints=web"
  - "traefik.http.routers.dashboard.service=api@internal"
```

`service=api@internal` es un servicio especial de Traefik que expone su propio panel de administración.

### Servicios actualmente expuestos

| Hostname | Puerto interno | Contenedor |
|----------|---------------|------------|
| `traefik.homelab` | Dashboard interno | traefik |
| `api.homelab` | 8000 | api |
| `homepage.homelab` | 3000 | homepage |
| `portainer.homelab` | 9000 | portainer |
| `n8n.homelab` | 5678 | n8n |
| `uptime.homelab` | 3001 | uptime-kuma |

## Cómo agregar un nuevo servicio

1. Crear el directorio `compose/<nombre>/` con su `compose.yaml`
2. Agregar los labels de Traefik según la convención
3. Ejecutar `docker compose -f compose/<nombre>/compose.yaml up -d`
4. Verificar con `curl -H "Host: <nombre>.homelab" http://127.0.0.1`

## Decisiones de diseño

### Fase 1 — Convivencia (estado actual)

- Traefik se agrega como punto de entrada adicional, sin reemplazar nada
- Todos los servicios mantienen sus puertos directos en el host
- Tailscale Funnel sigue apuntando directamente a la API en `127.0.0.1:8000`
- Sin TLS todavía (solo entrypoint `web` en puerto 80)
- Sin modificación del firewall DOCKER-USER

### Fase 2 — Unificación (futura)

- Remover puertos directos de los servicios
- Apuntar Tailscale Funnel a Traefik (`127.0.0.1:80`) en lugar de a la API
- Agregar entrypoint `websecure` con TLS (Let's Encrypt via DuckDNS)
- Agregar middleware de rate limiting, cabeceras de seguridad, etc.

### Host-based vs Path-based

Se eligió host-based routing porque:
- No requiere modificar las aplicaciones (no necesitan `--base-path` ni configuraciones especiales)
- Las URLs son más naturales (`http://portainer.homelab` vs `http://192.168.1.50/portainer`)
- Escala mejor al agregar servicios
- Prepara la infraestructura para cuando se tenga un DNS real con wildcard

Para usarlo se requiere configuración DNS local (no incorporada en esta fase). Mientras tanto, las pruebas se hacen con el header `Host` explícito.

### Sin cambios en HOMEPAGE_ALLOWED_HOSTS

Homepage requiere la variable `HOMEPAGE_ALLOWED_HOSTS` para validar el header `Host`. Se modificará solo si las pruebas con Traefik demuestran que es necesario.

### Seguridad

- Binding exclusivo a `127.0.0.1` — sin exposición a LAN ni Internet
- No hay TLS (se agregará en fase futura con Let's Encrypt)
- Dashboard accesible solo desde `localhost:8080`
- Tráfico entre contenedores en red `homelab` (bridge interna)

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `compose/traefik/compose.yaml` | Servicio Traefik |
| `compose/traefik/traefik.yml` | Configuración estática |
| `compose/traefik/.env.example` | Template (reservado) |
| `docs/traefik.md` | Esta documentación |

## Referencias

- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Traefik Docker Provider](https://doc.traefik.io/traefik/providers/docker/)
- [Traefik Router Configuration](https://doc.traefik.io/traefik/routing/routers/)
