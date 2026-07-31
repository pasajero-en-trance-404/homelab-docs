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

El dominio `homelab404-debian.duckdns.org` se actualiza automáticamente con la IP pública del servidor mediante systemd timer.

### Arquitectura

```
DuckDNS API → homelab404-debian.duckdns.org → 181.84.216.208 (IP pública)
                       │
         (futuro: reverse proxy en puerto 443)
                       │
              Servidor Debian
```

Actualmente DuckDNS no está vinculado directamente a Tailscale Funnel porque:
- DuckDNS solo admite registros A/AAAA (IPs)
- Funnel usa la infraestructura de Tailscale (dominio `.ts.net`)
- Para servir HTTPS en el dominio DuckDNS se necesita un reverse proxy (Traefik/Nginx) — fase futura

### Archivos

| Archivo | Propósito |
|---------|-----------|
| `scripts/duckdns/duckdns.sh` | Script de actualización |
| `scripts/duckdns/duckdns.service` | Systemd oneshot service |
| `scripts/duckdns/duckdns.timer` | Systemd timer (cada 5 min) |
| `scripts/duckdns/.env.example` | Template de configuración |

### Configuración

El token se almacena fuera del repositorio en:

```
~/homelab-data/duckdns/duckdns.conf
```

Formato del archivo:

```bash
DUCKDNS_DOMAIN=homelab404-debian
DUCKDNS_TOKEN=tu-token-aqui
```

### Instalación

```bash
# 1. Crear archivo de configuración
mkdir -p ~/homelab-data/duckdns
cat > ~/homelab-data/duckdns/duckdns.conf << 'EOF'
DUCKDNS_DOMAIN=homelab404-debian
DUCKDNS_TOKEN=<token>
EOF
chmod 600 ~/homelab-data/duckdns/duckdns.conf

# 2. Copiar units e iniciar timer
sudo cp scripts/duckdns/duckdns.service /etc/systemd/system/
sudo cp scripts/duckdns/duckdns.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now duckdns.timer
```

### Verificación

```bash
# Estado del timer
systemctl status duckdns.timer
systemctl list-timers --all | grep duckdns

# Logs del servicio
sudo journalctl -u duckdns.service
sudo journalctl -u duckdns.timer

# Resolución DNS
dig homelab404-debian.duckdns.org +short
nslookup homelab404-debian.duckdns.org

# Actualización manual (prueba)
curl -s "https://www.duckdns.org/update?domains=homelab404-debian&token=<token>&ip="
```

### Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `response=KO` | Token inválido | Verificar token en `~/homelab-data/duckdns/duckdns.conf` |
| Servicio falla con `status=203/EXEC` | Ruta del script incorrecta | Verificar `ExecStart` en el service unit |
| Timer no arranca | `duckdns.service` no encontrado | Verificar que el service unit está en `/etc/systemd/system/` |
| No se actualiza la IP | Sin conectividad a DuckDNS | Verificar con `curl -s https://www.duckdns.org` |
| `journalctl` no muestra logs | Usuario sin permisos | Usar `sudo journalctl` |
| `dig` no resuelve | DNS caché / DuckDNS propagación | Esperar 5 min y reintentar |

### Limitaciones

- El dominio DuckDNS solo resuelve a la IP pública, no hay TLS sin reverse proxy
- La IP se actualiza cada 5 minutos via systemd timer
- Si la IP pública cambia, puede haber hasta 5 minutos de desactualización
- DuckDNS no soporta CNAME ni reenvío a URLs de Tailscale

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
