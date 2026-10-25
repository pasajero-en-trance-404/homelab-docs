# Acceso remoto — Ubuntu → Debian

> **Última verificación:** 2026-10-25, ejecutada en `debian-server`.
> Este documento describe cómo administrar el servidor del homelab desde la computadora Ubuntu. Complementa `05-red.md` (red, firewall y SSH del servidor) y `docs/public-access.md` (Tailscale Funnel).

## 1. Objetivo y alcance

El acceso remoto permite administrar el servidor Debian desde la computadora Ubuntu sin depender de un monitor, teclado o sesión gráfica local.

Casos de uso:

- Abrir una shell en Debian y ejecutar comandos de administración.
- Trabajar con Git y los archivos de `homelab-docs`.
- Revisar contenedores, logs y servicios.
- Ejecutar OpenCode en Debian para que el agente trabaje directamente sobre los archivos del servidor.

Equipos que intervienen:

| Equipo | Rol | Datos de referencia |
|--------|-----|---------------------|
| Ubuntu | Computadora de trabajo | Ubuntu 24.04 LTS, usuario local `zer0tr4ce`, IP LAN observada `192.168.1.6` |
| Debian | Servidor del homelab | `debian-server`, Debian 13 (Trixie), usuario `administrador`, IP LAN `192.168.1.50`, IP Tailscale `100.119.176.84` |

> Los datos de Debian están verificados en la sección 3.1. Los datos de Ubuntu son reportados por el usuario y no se pudieron comprobar desde el servidor (ver 3.2).

Fuera de alcance:

- Escritorio remoto o control de la sesión gráfica XFCE.
- Wake-on-LAN.
- Exponer SSH a Internet.
- Publicar paneles administrativos por Tailscale Funnel.

## 2. Arquitectura

```text
Ubuntu (zer0tr4ce)
  │
  ├── LAN 192.168.1.6 ──────────────┐
  │                                  │  SSH TCP/22 (OpenSSH)
  └── Tailscale 100.87.61.109 ──┐    │
                                 ▼    ▼
                         debian-server
                         ├── LAN: 192.168.1.50/24 (enp3s0)
                         ├── Tailscale: 100.119.176.84 (tailscale0)
                         ├── MagicDNS: debian-server.taile532c7.ts.net
                         ├── sshd:22 — solo autenticación por clave
                         └── Docker: API, Traefik, Homepage, Portainer, n8n, Uptime Kuma
```

### Papel de cada mecanismo

| Mecanismo | Qué hace | Qué NO hace |
|-----------|----------|-------------|
| SSH por LAN | Abre una shell en Debian usando la IP `192.168.1.50` | No funciona fuera de la LAN |
| SSH por Tailscale | Abre la misma shell usando la IP del tailnet o MagicDNS | No es Tailscale SSH: es OpenSSH normal transportado por la red privada de Tailscale |
| Tailscale (servicios) | Da acceso privado a Homepage, Portainer, n8n y Uptime Kuma desde dispositivos del tailnet | No publica esos servicios en Internet |
| Tailscale Funnel | Publica **solo la API** en `https://debian-server.taile532c7.ts.net` | No publica SSH ni paneles administrativos |

### Diferencia clave: Tailscale privado vs. Funnel público

- **Tailscale (tailnet):** red privada entre los dispositivos autenticados. El tráfico SSH y el acceso a paneles administrativos viajan por esta red.
- **Tailscale Funnel:** publicación pública de un servicio concreto. En este servidor, Funnel enruta la raíz del dominio público a `http://127.0.0.1:8000`, que es la API.
- **SSH no está expuesto por Funnel.** El puerto 22 no se publica en la URL pública. Funnel y SSH son mecanismos independientes.

## 3. Estado actual de la configuración

### 3.1 Datos verificados en el servidor (2026-10-25)

| Dato | Valor verificado | Cómo se comprobó |
|------|------------------|------------------|
| Hostname | `debian-server` | `hostname`, `hostnamectl` |
| Sistema operativo | Debian GNU/Linux 13 (Trixie), kernel `6.12.96+deb13-amd64` | `hostnamectl`, `uname -a` |
| RAM total | ~3,0 GiB | `free -h` |
| Usuario remoto | `administrador` (uid 1000, grupos `sudo` y `docker`) | `whoami`, `id` |
| Repositorio | `/home/administrador/homelab-docs`, rama `main`, árbol limpio, HEAD `249d183` | `git status`, `git log -1` |
| Interfaz LAN | `enp3s0`, `192.168.1.50/24` | `ip -4 addr show` |
| Gateway | `192.168.1.1` | `ip route` |
| Interfaz Tailscale | `tailscale0`, `100.119.176.84/32` | `ip -4 addr show`, `tailscale ip -4` |
| MagicDNS | `debian-server.taile532c7.ts.net` | `tailscale status` |
| Versión Tailscale | `1.102.2` | `tailscale version` |
| Servicio Tailscale | `tailscaled.service` habilitado y activo | `systemctl is-enabled/is-active tailscaled` |
| Par Ubuntu en el tailnet | IP `100.87.61.109`, OS reportado `linux`, online | `tailscale status --json` |
| Servicio SSH | `ssh.service` habilitado y activo; escucha en `0.0.0.0:22` y `[::]:22` | `systemctl`, `ss -tln` |
| Claves autorizadas | 2 claves públicas Ed25519 en `~/.ssh/authorized_keys`; comentarios `administrador@debian-server` y `ubuntu-homelab` | `ls -l`, `awk` sobre metadatos, sin volcar claves |
| Permisos SSH | `~/.ssh` en `700`; `authorized_keys` en `600` | `ls -ld`, `ls -l` |
| OpenCode | Ejecutable en `/home/administrador/.opencode/bin/opencode`, versión `1.19.4` | ruta completa y shell interactiva |
| PATH de OpenCode | Línea `export PATH="$HOME/.opencode/bin:$PATH"` en `~/.bashrc` (línea 117) | `grep -n opencode ~/.bashrc` |
| API local | `http://127.0.0.1:8000/api/health` → HTTP 200 | `curl` |
| API pública | `https://debian-server.taile532c7.ts.net/api/health` → HTTP 200 | `curl` desde el servidor |
| Funnel | Activo; `/` → `http://127.0.0.1:8000` | `tailscale funnel status` |

Configuración SSH declarada en `/etc/ssh/sshd_config`:

| Directiva | Valor |
|-----------|-------|
| `PasswordAuthentication` | `no` |
| `PubkeyAuthentication` | `yes` |
| `PermitRootLogin` | `no` |
| `KbdInteractiveAuthentication` | `no` |
| `X11Forwarding` | `no` |

No hay archivos de override en `/etc/ssh/sshd_config.d/`. La directiva `Include /etc/ssh/sshd_config.d/*.conf` existe, pero el directorio está vacío.

> **Nota de verificación:** `sshd -T` (configuración efectiva) no se pudo ejecutar en esta sesión porque no se dispone de `sudo` no interactivo. Los valores anteriores se obtuvieron leyendo la configuración principal y comprobando que no hay drop-ins. El servicio SSH está activo.

Contenedores observados:

| Contenedor | Estado | Puertos publicados |
|------------|--------|--------------------|
| `api` | Up | `127.0.0.1:8000->8000/tcp` |
| `uptime-kuma` | Up (healthy) | `0.0.0.0:3001->3001/tcp` |
| `n8n` | Up | `0.0.0.0:5678->5678/tcp` |
| `portainer` | Up | `0.0.0.0:9000->9000/tcp` |
| `homepage` | Up (healthy) | `0.0.0.0:3000->3000/tcp` |
| `traefik` | Up | `127.0.0.1:80->80/tcp`, `127.0.0.1:8080->8080/tcp` |

> El estado de los contenedores es una foto del momento de la verificación; puede cambiar.

### 3.2 Datos históricos o del lado del cliente (no re-verificados en esta sesión)

Estos datos provienen del contexto de la tarea y de configuraciones previas. No se pudieron comprobar desde Debian porque pertenecen a la computadora Ubuntu o a sesiones anteriores:

- Ubuntu 24.04 LTS, usuario local `zer0tr4ce`.
- IP LAN observada en Ubuntu: `192.168.1.6`.
- Clave privada usada en Ubuntu: `~/.ssh/id_ed25519_homelab`.
- Acceso SSH exitoso desde Ubuntu por LAN (`192.168.1.50`) y por Tailscale (`100.119.176.84`) en sesiones previas.
- OpenCode no estaba inicialmente en el PATH y se localizó en `~/.opencode/bin/opencode`; después se agregó al PATH de `~/.bashrc`. **La configuración actual del PATH sí está verificada** (ver 3.1).
- Wake-on-LAN: no hay evidencia de que esté configurado o verificado.

> La clave pública del cliente aparece instalada en el servidor (comentario `ubuntu-homelab`), pero el nombre exacto del archivo privado en Ubuntu no puede confirmarse desde Debian.

## 4. Procedimiento de conexión desde Ubuntu

### 4.1 Requisitos previos

- El servidor debe estar encendido y conectado a la red.
- Para LAN: Ubuntu y Debian deben estar en la misma red (`192.168.1.0/24`).
- Para Tailscale: ambos equipos deben estar autenticados en el mismo tailnet y online.
- La clave privada debe existir en Ubuntu: `~/.ssh/id_ed25519_homelab`.
- La clave pública correspondiente debe estar en `/home/administrador/.ssh/authorized_keys` en Debian.

### 4.2 Conexión por IP local (LAN)

Desde Ubuntu:

```bash
ssh -i ~/.ssh/id_ed25519_homelab administrador@192.168.1.50
```

### 4.3 Conexión por Tailscale

Por IP del tailnet:

```bash
ssh -i ~/.ssh/id_ed25519_homelab administrador@100.119.176.84
```

Por MagicDNS (si está habilitado en el cliente):

```bash
ssh -i ~/.ssh/id_ed25519_homelab administrador@debian-server.taile532c7.ts.net
```

### 4.4 Cómo reconocer una conexión exitosa

- Aparece un prompt similar a:

  ```text
  administrador@debian-server:~$
  ```

- No se solicita contraseña (puede solicitarse la passphrase de la clave privada si tiene una).
- Estos comandos confirman que estás en el servidor:

  ```bash
  hostname          # debian-server
  whoami            # administrador
  ip -4 addr show tailscale0
  ```

- Si es la primera conexión, SSH puede pedir confirmación de la huella del host. Verifica que coincida con la del servidor antes de aceptar.

### 4.5 Cómo cerrar la sesión

```bash
exit
```

También funciona `Ctrl+D`.

### 4.6 Si la conexión falla

Orden recomendado de diagnóstico:

1. **Comprobar red y destino.**
   - LAN: `ping -c 3 192.168.1.50`
   - Tailscale: `tailscale status` en Ubuntu y en Debian.
2. **Comprobar que SSH está activo en Debian.**

   ```bash
   systemctl is-active ssh
   ss -tln | grep ':22'
   ```

3. **Ver la negociación SSH.**

   ```bash
   ssh -v -i ~/.ssh/id_ed25519_homelab administrador@192.168.1.50
   ```

4. **Revisar permisos de la clave en Ubuntu.**

   ```bash
   ls -l ~/.ssh/id_ed25519_homelab
   ```

   La clave privada no debe ser legible por otros usuarios. Si los permisos son incorrectos, SSH puede rechazarla.

5. **Revisar logs en Debian.**

   ```bash
   sudo journalctl -u ssh --no-pager -n 30
   ```

6. **Confirmar usuario y clave correctos.** El usuario es `administrador`; no se permite login directo como `root`.

No desactives `PasswordAuthentication`, `PermitRootLogin no` ni el firewall para “probar”. Si algo no funciona, corrige la causa.

## 5. Procedimiento para trabajar con OpenCode

OpenCode se ejecuta **en Debian**. Los comandos, rutas y cambios que haga el agente afectan los archivos del servidor, no los de Ubuntu.

### 5.1 Conectarse y ubicarse en el repositorio

Desde Ubuntu:

```bash
ssh -i ~/.ssh/id_ed25519_homelab administrador@192.168.1.50
```

Ya en Debian:

```bash
cd ~/homelab-docs
pwd
git status
```

`/home/administrador/homelab-docs` existe y es el repositorio del homelab (verificado).

### 5.2 Comprobar OpenCode

```bash
opencode --version
```

Resultado verificado al documentar: `1.19.4`.

Si el comando funciona, iniciar el agente:

```bash
opencode
```

### 5.3 Si `opencode` no se encuentra

Usar la ruta completa:

```bash
~/.opencode/bin/opencode --version
~/.opencode/bin/opencode
```

Comprobar si la línea de PATH ya existe:

```bash
grep -n 'opencode' ~/.bashrc
```

Si **no existe**, agregarla una sola vez:

```bash
echo 'export PATH="$HOME/.opencode/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

No agregar la línea de nuevo si ya está presente.

> En Debian, `~/.profile` incluye `~/.bashrc`, y `~/.bashrc` configura el PATH para shells interactivas. Una shell no interactiva (`bash -lc`) puede no cargar esa línea; una sesión SSH interactiva sí la carga. Si el comando funciona tras reconectarse, es normal.

### 5.4 Consideraciones

- OpenCode debe ejecutarse en una terminal interactiva (sesión SSH normal).
- El agente trabaja sobre los archivos del servidor. Revisar los cambios con `git diff` antes de confirmarlos.
- No pegar claves privadas, tokens ni contenido de `.env` en el chat del agente.
- Si se quiere trabajar sobre el repositorio local de Ubuntu, OpenCode debe ejecutarse en Ubuntu, no en Debian.

## 6. Verificaciones y pruebas

### 6.1 Pruebas realizadas y resultados

| Prueba | Resultado | Dónde se ejecutó |
|--------|-----------|------------------|
| Identidad del servidor (`hostname`, `hostnamectl`) | `debian-server`, Debian 13 | Debian |
| Memoria total (`free -h`) | ~3,0 GiB | Debian |
| Repositorio presente (`ls -ld ~/homelab-docs`) | Existe, propietario `administrador` | Debian |
| SSH activo (`systemctl is-active ssh`) | `active` | Debian |
| Puerto 22 escuchando (`ss -tln`) | `0.0.0.0:22` y `[::]:22` | Debian |
| Configuración SSH (`grep` en `sshd_config`) | Password `no`, root `no`, pubkey `yes`, X11 `no`, kbd-interactive `no` | Debian |
| Directorio de drop-ins SSH | Vacío | Debian |
| Claves autorizadas | 2 claves Ed25519; comentario `ubuntu-homelab` presente | Debian |
| Permisos de `~/.ssh` y `authorized_keys` | `700` y `600` | Debian |
| Tailscale activo | `tailscaled.service` enabled/active; versión `1.102.2` | Debian |
| IP Tailscale | `100.119.176.84` | Debian |
| Par Ubuntu en tailnet | `100.87.61.109`, online | Debian |
| Funnel | Activo; `/` → `http://127.0.0.1:8000` | Debian |
| API local | HTTP 200 en `/api/health` | Debian |
| API pública | HTTP 200 en `https://debian-server.taile532c7.ts.net/api/health` | Debian |
| Contenedores | 6 contenedores arriba | Debian |
| OpenCode | `1.19.4` en `~/.opencode/bin/opencode`; resuelto en shell interactiva | Debian |
| TCP/22 en IP LAN y Tailscale | Conexión TCP correcta desde el propio servidor | Debian |

> La prueba TCP contra las propias IPs solo confirma que `sshd` escucha en esas interfaces. No sustituye una autenticación real desde Ubuntu.

### 6.2 Comandos para repetir las pruebas

En Debian:

```bash
hostname
hostnamectl
free -h
ls -ld ~/homelab-docs
systemctl is-active ssh
ss -tln | grep ':22'
grep -RniE '^\s*(PasswordAuthentication|PermitRootLogin|PubkeyAuthentication|KbdInteractiveAuthentication|X11Forwarding)' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/
ls -ld ~/.ssh
ls -l ~/.ssh/authorized_keys
awk '{print $1, $3}' ~/.ssh/authorized_keys   # solo tipo y comentario, sin clave
tailscale status
tailscale ip -4
tailscale funnel status
docker ps
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/api/health
curl -sS -o /dev/null -w '%{http_code}\n' https://debian-server.taile532c7.ts.net/api/health
~/.opencode/bin/opencode --version
```

En Ubuntu:

```bash
ssh -i ~/.ssh/id_ed25519_homelab administrador@192.168.1.50
ssh -i ~/.ssh/id_ed25519_homelab administrador@100.119.176.84
tailscale status
curl -sS -o /dev/null -w '%{http_code}\n' https://debian-server.taile532c7.ts.net/api/health
```

### 6.3 Pruebas pendientes

- **Acceso SSH real desde Ubuntu en esta fecha.** No se ejecutó desde el cliente en esta sesión; se apoya en verificaciones previas del usuario y en el estado del servidor.
- **Acceso desde una red externa a la LAN.** Probar desde datos móviles u otra red:
  - SSH por Tailscale: `ssh -i ~/.ssh/id_ed25519_homelab administrador@debian-server.taile532c7.ts.net`
  - API pública: `curl https://debian-server.taile532c7.ts.net/api/health`
  - Registrar fecha, red y resultado.
- **Verificar en Ubuntu los datos del cliente:** versión exacta (`lsb_release -a`), usuario (`whoami`), IP LAN (`ip -4 addr`) y nombre del archivo de clave (`ls -l ~/.ssh`).
- **Confirmar que MagicDNS resuelve desde Ubuntu:** `getent hosts debian-server.taile532c7.ts.net` o `tailscale status`.
- **Wake-on-LAN:** evaluar si la placa/BIOS/NIC lo soportan. No asumir que está configurado.

## 7. Seguridad

Reglas aplicadas o recomendadas:

- **La clave privada SSH permanece en Ubuntu.** No copiarla al servidor, al repositorio, a un chat ni a un backup público.
- **No guardar credenciales en Git.** `.env`, tokens, contraseñas y claves privadas están fuera del repositorio. Los secretos del proyecto se manejan con el vault GPG documentado en `secrets/README.md`.
- **Mantener autenticación por clave.** `PasswordAuthentication no`, `PermitRootLogin no`, `X11Forwarding no`.
- **No abrir puertos en el router** sin una decisión explícita. Tailscale y Funnel no requieren abrir puertos entrantes.
- **Funnel es público y sin autenticación de Tailscale.** Solo debe apuntar a la API. No apuntar Funnel a SSH, Portainer, Homepage, n8n ni Uptime Kuma.
- **Los paneles administrativos son privados.** Se acceden por Tailscale o, en el caso de Homepage, por LAN según el firewall.
- **Revisar las claves autorizadas.** Actualmente hay 2 claves en `authorized_keys`; eliminar cualquier clave desconocida y rotar si hay sospecha.
- **El tailnet es la frontera de acceso privado.** Mantener los dispositivos autenticados y revisar la ACL/dispositivos en la consola de Tailscale.
- **No publicar secretos en la documentación.** Este documento no incluye claves privadas, tokens, contraseñas ni contenido de `.env`.
- **No usar `StrictHostKeyChecking=no` de forma permanente.** Verificar la huella del host en la primera conexión.
- **Evitar el reenvío de agente SSH (`-A`)** salvo que sea estrictamente necesario.

## 8. Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `opencode: command not found` | PATH no cargado o línea ausente en `~/.bashrc` | Usar `~/.opencode/bin/opencode`; comprobar `grep -n opencode ~/.bashrc`; agregar la línea solo si falta; reconectar o `source ~/.bashrc` |
| `opencode` funciona con ruta completa pero no por nombre | Shell no interactiva o PATH no cargado | Usar una sesión SSH interactiva; comprobar `bash -ic 'command -v opencode'` |
| `Permission denied (publickey)` | Clave incorrecta, no instalada o usuario equivocado | Verificar `-i`, usuario `administrador`, clave en `authorized_keys`; usar `ssh -v` |
| `WARNING: UNPROTECTED PRIVATE KEY FILE` | Permisos demasiado abiertos en Ubuntu | `chmod 700 ~/.ssh` y `chmod 600 ~/.ssh/id_ed25519_homelab`; no copiar la clave al servidor |
| Se pide contraseña y falla | La autenticación por contraseña está deshabilitada | Usar la clave correcta; no habilitar passwords como solución |
| Servidor inaccesible por LAN | Equipos en redes distintas, IP cambiada o servidor apagado | `ping 192.168.1.50`; comprobar IP en el servidor; confirmar que está encendido |
| Servidor inaccesible por Tailscale | Cliente o servidor offline, sesión vencida o ACL | `tailscale status` en ambos; `tailscale ping 100.119.176.84`; revisar autenticación del nodo |
| Funnel responde error | API caída o Funnel desconfigurado | `docker ps`, `curl http://127.0.0.1:8000/api/health`, `tailscale funnel status` |
| SSH funciona pero no hay escritorio remoto | SSH no depende de XFCE; la sesión gráfica puede estar ausente o bloqueada | SSH no inicia una sesión gráfica. No confundir conectividad de red con disponibilidad del escritorio |
| El servidor no responde tras estar apagado | Wake-on-LAN no configurado o no soportado | No asumir WOL; evaluar BIOS/NIC y documentarlo por separado |

## 9. Pendientes y próximos pasos

- [ ] Probar SSH por Tailscale desde una red externa real (datos móviles u otra red) y registrar el resultado.
- [ ] Probar la API pública desde una red externa y confirmar HTTP 200.
- [ ] Verificar en Ubuntu la versión, el usuario, la IP LAN y el archivo exacto de clave.
- [ ] Confirmar resolución MagicDNS desde Ubuntu.
- [ ] Evaluar Wake-on-LAN por separado (BIOS, placa ASUS A55BM-K, interfaz Ethernet).
- [ ] Opcional: crear un alias en `~/.ssh/config` de Ubuntu para no repetir `-i` ni el usuario:

  ```sshconfig
  Host homelab
      HostName debian-server.taile532c7.ts.net
      User administrador
      IdentityFile ~/.ssh/id_ed25519_homelab
      IdentitiesOnly yes
  ```

  Con ese alias, la conexión sería `ssh homelab`. No se aplicó en esta sesión.
- [ ] Mantener actualizada la versión de Tailscale en `05-red.md` cuando se actualice el paquete.

## 10. Comandos de referencia

### Desde Ubuntu (cliente)

```bash
# Conexión por LAN
ssh -i ~/.ssh/id_ed25519_homelab administrador@192.168.1.50

# Conexión por Tailscale (IP)
ssh -i ~/.ssh/id_ed25519_homelab administrador@100.119.176.84

# Conexión por MagicDNS
ssh -i ~/.ssh/id_ed25519_homelab administrador@debian-server.taile532c7.ts.net

# Diagnóstico de autenticación
ssh -v -i ~/.ssh/id_ed25519_homelab administrador@192.168.1.50

# Permisos de la clave
ls -ld ~/.ssh
ls -l ~/.ssh/id_ed25519_homelab
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519_homelab

# Estado del tailnet
tailscale status
tailscale ping 100.119.176.84

# API pública
curl -sS -o /dev/null -w '%{http_code}\n' https://debian-server.taile532c7.ts.net/api/health
```

### Desde Debian (servidor)

```bash
# Identidad y estado
hostname
hostnamectl
whoami
free -h
uptime

# Repositorio
cd ~/homelab-docs
pwd
git status
git log -1 --oneline

# SSH
systemctl status ssh
ss -tln | grep ':22'
grep -RniE '^\s*(PasswordAuthentication|PermitRootLogin|PubkeyAuthentication|KbdInteractiveAuthentication|X11Forwarding)' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/
ls -ld ~/.ssh
ls -l ~/.ssh/authorized_keys
awk '{print $1, $3}' ~/.ssh/authorized_keys   # solo tipo y comentario
sudo journalctl -u ssh --no-pager -n 30

# Tailscale
tailscale status
tailscale ip -4
tailscale version
tailscale funnel status
tailscale ping 100.87.61.109

# Servicios y API
docker ps
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/api/health
curl -sS -o /dev/null -w '%{http_code}\n' https://debian-server.taile532c7.ts.net/api/health

# OpenCode
cd ~/homelab-docs
opencode --version
opencode
# Si falla:
~/.opencode/bin/opencode --version
grep -n 'opencode' ~/.bashrc
```

## Referencias

- `05-red.md` — configuración de red, Tailscale, firewall y SSH del servidor.
- `docs/public-access.md` — Tailscale Funnel, DuckDNS y superficie pública.
- `docs/dr.md` — reconstrucción del servidor y verificación posterior.
- `secrets/README.md` — manejo de secretos y vault GPG.
- [Tailscale Funnel](https://tailscale.com/kb/1223/tailscale-funnel)
- [Tailscale SSH](https://tailscale.com/kb/1193/tailscale-ssh) — no usado en esta configuración.
