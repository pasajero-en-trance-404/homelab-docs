# Comandos útiles

## Docker

```bash
# Listar contenedores en ejecución
docker ps

# Listar todos los contenedores
docker ps -a

# Ver logs de un contenedor
docker logs -f <nombre>

# Ver estado de recursos de Docker
docker system df

# Inspeccionar detalles de red de un contenedor
docker inspect <nombre> --format '{{json .NetworkSettings.Networks}}' | python3 -m json.tool

# Listar redes Docker
docker network ls

# Ver redes de un contenedor
docker inspect <nombre> --format '{{.NetworkSettings.Networks}}'

# Ver información del sistema Docker
docker info
```

## Docker Compose

```bash
# Validar sintaxis de un compose
docker compose -f compose/<servicio>/compose.yaml config

# Iniciar servicio
docker compose -f compose/<servicio>/compose.yaml up -d

# Detener servicio
docker compose -f compose/<servicio>/compose.yaml down

# Ver logs
docker compose -f compose/<servicio>/compose.yaml logs -f

# Recrear contenedor
docker compose -f compose/<servicio>/compose.yaml up -d --force-recreate
```

## Red

```bash
# Ver interfaces de red
ip addr

# Ver IP de un contenedor
docker inspect <nombre> --format '{{.NetworkSettings.Networks.homelab.IPAddress}}'

# Ver gateway y DNS
ip route
resolvectl status
```

## Sistema

```bash
# Ver disco
df -h

# Ver uso de RAM y CPU
htop
btop

# Ver procesos
ps aux

# Ver versión de Debian
cat /etc/os-release

# Ver zona horaria
timedatectl

# Ver espacio usado por datos persistentes
du -sh ~/homelab-data/*/
```

## Git

```bash
# Ver estado del repositorio
git status

# Ver cambios realizados
git diff --staged

# Ver historial reciente
git log --oneline -10

# Agregar archivos al stage
git add <archivo>

# Commit
git commit -m "mensaje descriptivo"
```

## Firewall

```bash
# Ver reglas DOCKER-USER activas
sudo iptables -L DOCKER-USER -n --line-numbers -v

# Re-aplicar reglas
sudo systemctl restart docker-user-restore.service

# Deshabilitar temporalmente
sudo iptables -F DOCKER-USER

# Restaurar desde snapshot
sudo iptables-restore < /etc/iptables/rules.v4.backup

# Ver logs del restore
sudo journalctl -u docker-user-restore.service

# Estado del servicio
sudo systemctl status docker-user-restore.service

# Ver reglas de NAT de Docker
sudo iptables -t nat -L -n --line-numbers

# Ver ruleset completo en nftables
sudo nft list ruleset
```

## Tailscale

```bash
# Estado de conexión
tailscale status

# Versión
tailscale version

# Interfaz
ip addr show tailscale0

# Logs del daemon
journalctl -u tailscaled --no-pager -n 30

# Acceso remoto a servicios (desde otro dispositivo en el tailnet)
curl http://100.119.176.84:3000   # Homepage
curl http://100.119.176.84:9000   # Portainer
curl http://100.119.176.84:5678   # n8n
curl http://100.119.176.84:3001   # Uptime Kuma

# SSH via Tailscale
ssh administrador@100.119.176.84
# O via MagicDNS
ssh administrador@debian-server.taile532c7.ts.net
```

## SSH

```bash
# Verificar configuración activa de sshd
sudo sshd -T | grep -E "passwordauth|permitroot|pubkeyauth|x11forward"

# Probar autenticación local con clave
ssh -o PasswordAuthentication=no -o PreferredAuthentications=publickey -i ~/.ssh/homelab localhost

# Ver sesiones SSH activas
ss -tnp | grep :22
who

# Ver logs de autenticación SSH
sudo journalctl -u ssh --no-pager -n 20
```

## Backups

```bash
# Ejecutar backup manualmente
sudo systemctl start backup.service

# Ver estado del timer
systemctl status backup.timer
systemctl list-timers | grep backup

# Ver últimas líneas del log de backup
tail -20 ~/backups/backup.log

# Listar backups disponibles
ls -lh ~/backups/homelab-*.tar.gz

# Verificar integridad de un backup
tar -tzf ~/backups/homelab-*.tar.gz | head -20
```

## Logs y troubleshooting

```bash
# Ver logs de Docker Engine
journalctl -u docker --since "1 hour ago"

# Ver logs de servicios del sistema
journalctl -xe

# Ver puertos en escucha
ss -tlnp

# Ver procesos de Docker
docker top <nombre>

# Ver logs de un contenedor
docker logs -f <nombre>

# Ver uso de recursos de todos los contenedores
docker stats --no-stream

# Ver todas las redes Docker
docker network ls

# Inspeccionar contenedor (IP, red, mounts)
docker inspect <nombre>
```
