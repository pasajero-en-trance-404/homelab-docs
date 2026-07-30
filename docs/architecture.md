# Arquitectura del homelab

## Diagrama general

```
                    ┌─────────────────────────────────────┐
                    │         Internet                    │
                    └──────────────┬──────────────────────┘
                                   │
                           ┌────────▼────────┐
                           │ Tailscale Funnel│
                           │ /api → :8000    │
                           │ (TLS público)   │
                           └────────┬────────┘
                                   │
                           ┌────────▼────────┐
                           │   Tailscale     │
                           │  100.119.176.84 │
                           │  MagicDNS:      │
                           │  debian-server  │
                           │  .taile532c7    │
                           │  .ts.net        │
                           └────────┬────────┘
                                   │ wireguard
                                   │ (cifrado)
                           ┌────────▼────────┐
                           │   Router LAN    │
                           │  192.168.1.1    │
                           └────────┬────────┘
                                   │
                           ┌────────▼────────┐
                           │   Servidor      │
                           │  Debian 13      │
                           │  192.168.1.50   │
                           │  enp3s0         │
                           └────────┬────────┘
                                   │
                     ┌──────────────┼──────────────┐
                     │              │              │
               ┌─────▼─────┐  ┌────▼────┐  ┌─────▼─────┐
               │  SSH (22) │  │ Firewall│  │  Docker   │
               │  solo key │  │ DOCKER- │  │ Engine    │
               │           │  │ USER    │  │ 29.6.2    │
               └───────────┘  └────┬────┘  └─────┬─────┘
                                   │              │
                           ┌───────┴──────────────┴───────┐
                           │     Red homelab (172.22.0)   │
                           │  Bridge externo (br-bd61d7)  │
                           └───────┬──────────────┬───────┘
                                   │              │
               ┌───────────────────┼──────────────┼───────────────────┐
               │                   │              │                   │
         ┌─────▼─────┐      ┌─────▼─────┐  ┌─────▼─────┐      ┌─────▼─────┐
         │    API    │      │  Homepage │  │ Portainer │      │   n8n     │
         │   :8000   │      │   :3000   │  │   :9000   │      │   :5678   │
         │  pública  │      │  privado  │  │  privado  │      │  privado  │
         └───────────┘      └───────────┘  └───────────┘      └───────────┘
                                                              ┌───────────┐
                                                              │Uptime Kuma│
                                                              │   :3001   │
                                                              │  privado  │
                                                              └───────────┘
```

## Arquitectura Docker

### Redes

| Red | Driver | Subnet | Propósito |
|-----|--------|--------|-----------|
| `homelab` | bridge (external) | 172.22.0.0/16 | Comunicación entre servicios |
| `bridge` (docker0) | bridge | 172.17.0.0/16 | Default (vacío) |
| `homepage_default` | bridge | 172.21.0.0/16 | Residual (vacío) |
| `n8n_default` | bridge | 172.20.0.0/16 | Residual (vacío) |
| `portainer_default` | bridge | 172.18.0.0/16 | Residual (vacío) |
| `uptime-kuma_default` | bridge | 172.19.0.0/16 | Residual (vacío) |

Todos los contenedores activos están conectados únicamente a `homelab`. Las redes `*_default` se crearon automáticamente al levantar cada servicio por primera vez y ya no se usan.

### Contenedores

| Nombre | IP en homelab | Puertos expuestos |
|--------|---------------|-------------------|
| api | 172.22.0.x | 8000 |
| homepage | 172.22.0.2 | 3000 |
| portainer | 172.22.0.3 | 9000 |
| uptime-kuma | 172.22.0.4 | 3001 |
| n8n | 172.22.0.5 | 5678 |

### Volúmenes

Todos los datos persistentes usan bind mounts desde `~/homelab-data/<servicio>/` a rutas dentro del contenedor. No se usan named volumes de Docker.

La API no necesita almacenamiento persistente, solo el archivo `.env` en `~/homelab-data/api/`.

### Acceso al socket Docker

- Portainer: `docker.sock` en modo **rw** (gestión de contenedores)
- Homepage: `docker.sock` en modo **ro** (dashboard de estado)

---

## Arquitectura de red

### Interfaces

| Interfaz | IP | Propósito |
|----------|----|-----------|
| `enp3s0` | 192.168.1.50/24 | LAN física |
| `tailscale0` | 100.119.176.84/32 | Tailscale VPN |
| `lo` | 127.0.0.1 | Loopback |

### DNS

El sistema usa Tailscale DNS (`100.100.100.100`) como resolutor principal, con MagicDNS habilitado. El search domain del tailnet es `taile532c7.ts.net`.

Configuración DNS:
- Primario: Tailscale (100.100.100.100)
- Resolutores del sistema: 192.168.1.1, 1.1.1.1

### Firewall

#### Cadenas iptables-nft

El sistema usa `iptables-nft` (backend iptables sobre nftables). Tres actores gestionan las reglas:

1. **Tailscale** (`ts-input`, `ts-forward`, `ts-postrouting`)
2. **Docker** (`DOCKER`, `DOCKER-FORWARD`, `DOCKER-USER`, etc.)
3. **Admin** (DOCKER-USER — único punto de configuración manual)

#### Flujo de paquetes FORWARD

```
FORWARD (policy DROP)
  ├── ts-forward (marcado de paquetes Tailscale)
  ├── DOCKER-USER (reglas del admin)
  │     ├── ACCEPT si RELATED,ESTABLISHED
  │     ├── ACCEPT si iif = tailscale0
  │     ├── ACCEPT si iif = br+/docker0 (puertos 53,80,443,icmp)
  │     ├── ACCEPT si src=192.168.1.0/24 y dport=3000
  │     └── DROP resto
  └── DOCKER-FORWARD (reglas Docker para routing a contenedores)
```

#### Persistencia

```
Boot:
  network → docker.service (crea DOCKER-USER)
         → docker-user-restore.service (aplica reglas)
         → multi-user.target
```

---

## Flujo de backups

```
backup.timer (03:00 daily)
  └─ backup.service (User=root)
       └─ backup.sh
            ├─ Verificar Docker
            ├─ Detener: n8n, uptime-kuma, portainer
            ├─ Esperar flush SQLite (15s max)
            ├─ tar -czf ~/backups/homelab-<fecha>.tar.gz
            │    ├─ ~/homelab-data/
            │    └─ ~/homelab-docs/ (excluye .git y .env)
            ├─ Re-iniciar contenedores
            ├─ Verificar contenedores
            └─ Prune backups (retención: 7 diarios + 4 semanales)
```

---

## Relaciones entre servicios

```
Uptime Kuma
  ├─ Monitorea: homepage, portainer, n8n
  └─ Notifica: (pendiente configurar)

Homepage
  ├─ Muestra estado de: homepage, portainer, n8n, uptime-kuma
  │   (via docker.sock)
  └─ Provee dashboard con: bookmarks, enlaces a servicios

Portainer
  └─ Administra: homepage, n8n, uptime-kuma (via docker.sock)

n8n
  └─ Automatiza: (pendiente crear workflows)
```

---

## Acceso a servicios

| Origen | API | Homepage | Portainer | n8n | Uptime Kuma |
|--------|:---:|:--------:|:---------:|:---:|:-----------:|
| LAN (192.168.1.0/24) | ❌ | ✅ | ❌ | ❌ | ❌ |
| Tailscale (tailnet) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Internet (Funnel) | ✅ | ❌ | ❌ | ❌ | ❌ |

- Puerto 22 (SSH): solo accesible por clave, desde LAN o Tailscale.
- La API se accede desde Internet vía Tailscale Funnel en `https://debian-server.taile532c7.ts.net/api`.
- Los servicios administrativos se acceden directamente por Tailscale (IP/hostname del tailnet) o por bind a LAN.
