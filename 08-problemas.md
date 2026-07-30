# Problemas encontrados

Historial de incidencias relevantes durante la construcción y configuración del servidor.

---

## 1. Usuario sin permisos sudo

**Fecha**: 2026-07-27

**Problema**: El usuario `administrador` no podía ejecutar comandos con `sudo`.

**Causa**: El usuario no pertenecía al grupo `sudo` tras la instalación de Debian.

**Solución**:
```bash
su -  # o reiniciar y entrar como root
usermod -aG sudo administrador
```
Verificado con:
```bash
sudo whoami
# → root
```

---

## 2. Red de n8n — bridge por defecto en vez de homelab

**Fecha**: 2026-07-28

**Problema**: n8n se conectó a la red por defecto del compose (`n8n_default`) en vez de la red externa `homelab`, quedando aislado de los demás servicios.

**Causa**: El `compose.yaml` original de n8n no declaraba `networks: homelab: external: true` ni asignaba la red al servicio.

**Solución**:
```yaml
networks:
  homelab:
    external: true

services:
  n8n:
    networks:
      - homelab
```
Verificado con `docker inspect n8n --format '{{.NetworkSettings.Networks}}'`.

---

## 3. Migración de docker-compose.yml a compose.yaml

**Fecha**: 2026-07-28

**Problema**: Portainer tenía un archivo `docker-compose.yml` legacy junto al nuevo `compose.yaml`, causando confusión sobre cuál estaba activo.

**Causa**: Docker Compose v2+ prefiere `compose.yaml` sobre `docker-compose.yml`. El archivo legacy quedó como residuo de la configuración inicial.

**Solución**:
- Se migró Portainer a `compose.yaml`.
- El archivo legacy `docker-compose.yml` fue reemplazado por `compose.yaml`.
- Los demás servicios se crearon directamente con `compose.yaml`.

---

## 4. Permisos root de Portainer para backups

**Fecha**: 2026-07-29

**Problema**: Los datos de Portainer (`~/homelab-data/portainer/`) pertenecen a `root`, lo que impedía al usuario `administrador` leerlos para backups.

**Causa**: Portainer corre como root dentro del contenedor y crea archivos con permisos de root en el bind mount.

**Solución**: El script de backup (`backup/backup.sh`) se ejecuta como `User=root` via systemd timer. Esto permite leer los datos de Portainer sin problemas.

```ini
[Service]
User=root
ExecStart=/home/administrador/homelab-docs/backup/backup.sh
```

---

## 5. Endurecimiento SSH

**Fecha**: 2026-07-29

**Problema**: La configuración SSH del servidor permitía autenticación por contraseña y X11 forwarding, con riesgo de ataques de fuerza bruta.

**Causa**: Configuración por defecto de OpenSSH en Debian.

**Solución**: Se modificó `/etc/ssh/sshd_config`:
```
PasswordAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
X11Forwarding no
KbdInteractiveAuthentication no
```
Se verificó que la autenticación por clave funciona antes de deshabilitar passwords. Se reinició sshd para aplicar cambios.

---

## 6. Persistencia del firewall DOCKER-USER

**Fecha**: 2026-07-29

**Problema**: Las reglas de firewall agregadas a la cadena `DOCKER-USER` se pierden al reiniciar el servidor, porque Docker recrea la cadena vacía al iniciar.

**Causa**: Docker no persiste las reglas de DOCKER-USER entre reinicios del sistema.

**Solución**: Se creó:
- Script de restore: `/usr/local/sbin/restore-docker-user.sh`
- Servicio systemd: `docker-user-restore.service`
  - `After=docker.service tailscaled.service`
  - `Requires=docker.service`
  - Espera hasta 30 segundos a que Docker cree la cadena DOCKER-USER
  - Usa `flock` para evitar ejecuciones concurrentes
  - Registra en `journald` mediante `logger`

Verificado con `systemctl restart docker` y comprobando que las reglas se restauran.
