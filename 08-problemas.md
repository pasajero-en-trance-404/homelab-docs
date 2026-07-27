# Problemas encontrados

## Usuario sin permisos sudo

### Problema

El usuario administrador no podía ejecutar comandos con sudo.

### Solución

Se agregó el usuario al grupo sudo.

Se verificó con:

```bash
sudo whoami
```

Resultado:

```text
root
```
