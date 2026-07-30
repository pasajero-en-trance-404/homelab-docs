# 🖥️ Homelab Debian

> Transformando una PC antigua en un laboratorio personal para aprender Linux, Docker, redes, automatización e IA.

---

## 📖 Sobre este proyecto

Este repositorio documenta, paso a paso, el proceso de convertir una computadora antigua en un **homelab**.

La idea no es solamente mostrar el resultado final, sino registrar cada decisión técnica, cada error y cada aprendizaje durante el camino.

Todo lo que se instala, configura o modifica queda documentado.

---

## 🎯 Objetivos

- Aprender Linux desde la práctica.
- Administrar un servidor Debian.
- Aprender Docker y Docker Compose.
- Automatizar procesos con n8n.
- Administrar servicios mediante Portainer.
- Acceder remotamente con Tailscale.
- Asegurar el servidor con firewall y SSH hardening.
- Automatizar backups.
- Documentar todo el proceso.

---

## 🖥️ Hardware

| Componente | Especificación |
|------------|----------------|
| CPU | AMD A4-4000 APU (2 cores, 3.0 GHz) |
| RAM | 4 GB DDR3 (3 GB disponibles, objetivo: 8 GB) |
| Disco | SSD 120 GB (60 GB partición sistema, 20% usado) |
| Placa | ASUS A55BM-K (2014) |
| Red | Ethernet 1000 Mbps |

---

## 📂 Documentación

| Archivo | Contenido |
|---------|-----------|
| 00-estado-inicial.md | Estado inicial del proyecto |
| 01-hardware.md | Hardware utilizado |
| 02-instalacion-debian.md | Instalación paso a paso |
| 03-sistema-base.md | Configuración inicial |
| 04-docker.md | Docker |
| 05-red.md | Red, Tailscale, firewall, SSH |
| 06-servicios.md | Servicios instalados |
| 07-automatizacion.md | Automatizaciones (n8n) |
| 08-problemas.md | Errores encontrados y soluciones |
| 09-comandos-utiles.md | Comandos de referencia |
| docs/architecture.md | Arquitectura general del homelab |
| docs/public-access.md | Acceso público (Tailscale Funnel) |
| CHANGELOG.md | Historial de cambios del proyecto |
| AGENTS.md | Contexto para agentes de IA |

---

## 🚀 Estado del proyecto

### Implementado

- [x] Instalación de Debian 13 (Trixie)
- [x] Dual Boot con Windows
- [x] Entorno gráfico XFCE
- [x] Docker Engine 29.6.2 + Compose v5.3.1
- [x] Portainer — Administración de contenedores
- [x] Homepage — Dashboard de servicios
- [x] n8n — Automatización low-code
- [x] Uptime Kuma — Monitoreo de uptime
- [x] Tailscale — Acceso remoto seguro
- [x] SSH hardening — Solo clave, sin root, sin X11
- [x] Firewall persistente (DOCKER-USER) — Bloqueo LAN no autorizada
- [x] Backups automáticos — Diarios con retención

### Servicios públicos

- [x] Tailscale Funnel — Exposición pública de la API sin abrir puertos
- [x] API pública (FastAPI) — `GET /api`, `GET /api/health`

### Pendiente

- [ ] Reverse proxy (Traefik / Nginx Proxy Manager) — TLS, dominios
- [ ] OpenCode — Agente de IA local
- [ ] Base de datos (PostgreSQL / SQLite)
- [ ] Monitoreo y alertas (Prometheus + Grafana)
- [ ] Ampliación de RAM a 8 GB

---

## 📌 Filosofía

> Documentar primero. Instalar después.

Cada cambio realizado en el servidor queda registrado en este repositorio para poder reconstruir el proyecto desde cero.
