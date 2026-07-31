# Ansible — Homelab

Infraestructura como código del homelab, incorporada **progresivamente**.

## Estado actual (v1.1)

| Componente | Estado |
|------------|--------|
| `playbooks/site.yml` | Activo: ejecuta `bootstrap.sh` + verificación |
| `roles/base` | Planificado (no activo) |
| `roles/docker` | Planificado (no activo) |
| `roles/tailscale` | Planificado (no activo) |
| `roles/firewall` | Planificado (no activo) |
| `roles/compose` | Planificado (no activo) |
| `roles/systemd` | Planificado (no activo) |
| `roles/verify` | Activo |

## Estrategia progresiva

1. **Fase 1 (actual)**: `bootstrap.sh` es la fuente de verdad única. El playbook lo ejecuta vía el módulo `script`.
2. **Fase 2**: cada rol migra un paso del bootstrap (`base`, `docker`, `tailscale`, ...). El rol pasa a activo y el paso se marca como migrado en el script.
3. **Fase 3**: cuando todos los roles estén activos, `bootstrap.sh` queda solo como fallback de emergencia y referencia.

**Regla**: nunca duplicar lógica entre el script y un rol activo. Un paso vive en un solo lugar.

## Uso

```bash
# Instalar dependencias (solo la primera vez)
ansible-galaxy collection install -r requirements.yml

# Ejecutar todo
ansible-playbook -i inventory/hosts.yml playbooks/site.yml

# Solo bootstrap (sin verify)
ansible-playbook playbooks/site.yml --tags bootstrap

# Solo verificación
ansible-playbook playbooks/site.yml --tags verify
```

## Requisitos

- Ansible instalado en la máquina de control.
- Conexión SSH por clave al host (ver `inventory/hosts.yml`).
- Roles `community.docker` y `community.general` (ver `requirements.yml`).
