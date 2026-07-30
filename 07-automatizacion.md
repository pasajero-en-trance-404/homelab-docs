# Automatizaciones

## Estado actual

n8n está instalado y operativo, pero todavía no posee workflows creados ni documentados.

| Aspecto | Detalle |
|---------|---------|
| URL | http://192.168.1.50:5678 |
| Acceso remoto | http://100.119.176.84:5678 (via Tailscale) |
| Imagen | docker.n8n.io/n8nio/n8n:latest |
| Puerto | 5678 |
| Red Docker | homelab (172.22.0.0/16) |
| Datos | `~/homelab-data/n8n/` |
| Variables | `N8N_PORT=5678`, `N8N_SECURE_COOKIE=false` |

## Próximos workflows

Ideas para automatizaciones a implementar:

- Backup remoto: subir backups a ubicación externa (rsync, S3, BorgBase)
- Verificación de backup diario: notificar si el backup falló o está incompleto
- Alertas de servicios: monitorear estado de contenedores desde n8n
- Scraping periódico: recolectar métricas de servicios y guardarlas
- Notificaciones: integración con Telegram o email para eventos del servidor

Los workflows se documentarán a medida que se creen.
