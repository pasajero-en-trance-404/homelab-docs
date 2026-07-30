# Red

## Configuración de red

Interfaz:

enp3s0

Tipo:

Ethernet

Configuración:

IP estática configurada mediante NetworkManager.

IP:

192.168.1.50/24

Gateway:

192.168.1.1

DNS:

192.168.1.1
1.1.1.1

## Tailscale

Tailscale está instalado y activo. Puerta de entrada remota al servidor.

| Aspecto | Valor |
|---------|-------|
| Versión | 1.98.9 |
| IP tailnet | `100.119.176.84` / `fd7a:115c:a1e0::ef01:b0cc` |
| MagicDNS | `debian-server.taile532c7.ts.net` |
| Interfaz | `tailscale0` |
| Daemon | `tailscaled.service` — enabled, running |

Todos los servicios Docker son accesibles vía Tailscale. Homepage, Portainer, n8n y Uptime Kuma responden en sus puertos habituales a través de la IP de Tailscale.

### Acceso remoto

```bash
# Desde cualquier dispositivo en el tailnet:
ssh administrador@100.119.176.84
# O via MagicDNS:
ssh administrador@debian-server.taile532c7.ts.net

# Servicios web via Tailscale IP:
http://100.119.176.84:3000   # Homepage
http://100.119.176.84:9000   # Portainer
http://100.119.176.84:5678   # n8n
http://100.119.176.84:3001   # Uptime Kuma
```

## Firewall (DOCKER-USER)

Arquitectura: `iptables-nft` (backend iptables sobre nftables). Docker administra sus propias cadenas. Las reglas de firewall personalizadas se agregan en `DOCKER-USER`, la cadena de admin que Docker respeta y no modifica.

No se usa UFW. No se modificó la política INPUT (default ACCEPT). Solo se filtra tráfico FORWARD (contenedores Docker).

### Reglas aplicadas

| # | Regla | Efecto |
|---|-------|--------|
| 1 | `ctstate RELATED,ESTABLISHED` | Mantiene conexiones activas |
| 2 | `-i tailscale0` | Todo el tráfico desde Tailscale |
| 3-4 | `-i br+ dport 53 (udp+tcp)` | DNS desde contenedores |
| 5-6 | `-i docker0 dport 53 (udp+tcp)` | DNS desde bridge default |
| 7 | `-i br+ dport 80,443` | HTTP/HTTPS desde contenedores |
| 8 | `-i docker0 dport 80,443` | HTTP/HTTPS desde bridge default |
| 9-10 | `-i br+ icmp echo` | Ping desde contenedores |
| 11-12 | `-i docker0 icmp echo` | Ping desde bridge default |
| 13 | `-s 192.168.1.0/24 dport 3000` | Homepage accesible desde LAN |
| 14 | DROP | Bloquea todo lo demás |

### Política por servicio

| Puerto | Servicio | LAN | Tailscale | Internet |
|--------|----------|:---:|:---------:|:--------:|
| 3000 | Homepage | ✅ | ✅ | ❌ |
| 9000 | Portainer | ❌ | ✅ | ❌ |
| 5678 | n8n | ❌ | ✅ | ❌ |
| 3001 | Uptime Kuma | ❌ | ✅ | ❌ |
| Salida (80,443,53,ICMP) | Todos los contenedores | ✅ | ✅ | ✅ |

### Persistencia entre reinicios

Las reglas se restauran automáticamente al boot mediante un servicio systemd:

```
Boot sequence
├── docker.service          → crea DOCKER-USER (vacía)
├── tailscaled.service       → crea ts-* chains
├── docker-user-restore.service → aplica reglas
└── multi-user.target        → firewall activo
```

| Componente | Ruta |
|------------|------|
| Script de restore | `/usr/local/sbin/restore-docker-user.sh` |
| Service unit | `/etc/systemd/system/docker-user-restore.service` |
| Snapshot completo | `/etc/iptables/rules.v4.backup` |
| Fuente en repo | `compose/firewall/restore-docker-user.sh` |
| Fuente en repo | `compose/firewall/docker-user-restore.service` |

### Gestión del firewall

```bash
# Ver reglas aplicadas
sudo iptables -L DOCKER-USER -n --line-numbers -v

# Ver estadísticas de paquetes
sudo iptables -L DOCKER-USER -n -v

# Re-aplicar reglas manualmente (útil tras cambios)
sudo systemctl restart docker-user-restore.service

# Deshabilitar temporalmente (flushea reglas, no policy)
sudo iptables -F DOCKER-USER

# Restaurar desde snapshot
sudo iptables-restore < /etc/iptables/rules.v4.backup

# Ver logs del servicio
sudo journalctl -u docker-user-restore.service

# Estado del servicio
sudo systemctl status docker-user-restore.service
```

## SSH

| Directiva | Valor |
|-----------|-------|
| `PasswordAuthentication` | no |
| `PubkeyAuthentication` | yes |
| `PermitRootLogin` | no |
| `KbdInteractiveAuthentication` | no |
| `X11Forwarding` | no |

Solo acceso por clave SSH. No hay acceso por contraseña. Deshabilitado root login.

## Comandos utilizados

### Red

```bash
# Ver interfaces de red
ip addr

# Ver tabla de rutas
ip route

# Resolver un nombre de host
resolvectl status
```

### Tailscale

```bash
# Estado de la conexión
tailscale status

# Versión instalada
tailscale version

# Interfaces (ver tailscale0)
ip addr show tailscale0

# Logs del daemon
journalctl -u tailscaled --no-pager -n 30

# Probar conectividad a otro nodo del tailnet
ping 100.x.x.x
```

### Firewall

```bash
# Ver reglas DOCKER-USER activas
sudo iptables -L DOCKER-USER -n --line-numbers -v

# Ver estadísticas de paquetes
sudo iptables -L DOCKER-USER -n -v

# Re-aplicar reglas (útil tras cambios)
sudo systemctl restart docker-user-restore.service

# Deshabilitar temporalmente (flushea reglas)
sudo iptables -F DOCKER-USER

# Restaurar desde snapshot
sudo iptables-restore < /etc/iptables/rules.v4.backup

# Ver logs del servicio
sudo journalctl -u docker-user-restore.service

# Ver reglas de NAT (forwarding de puertos Docker)
sudo iptables -t nat -L -n --line-numbers

# Ver ruleset completo en formato nftables
sudo nft list ruleset | head -80
```

### SSH

```bash
# Verificar config activa
sshd -T 2>/dev/null | grep -E "passwordauth|permitroot|pubkeyauth"

# Test conexión local con clave
ssh -o PasswordAuthentication=no -o PreferredAuthentications=publickey -i ~/.ssh/homelab localhost

# Ver sesiones SSH activas
ss -tnp | grep :22
who
```
