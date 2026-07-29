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
```
