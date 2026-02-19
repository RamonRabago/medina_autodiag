# Reset Base de Datos a Cero

Script para vaciar todas las tablas y dejar solo al administrador (Ramon).

## Uso

```bash
# Activar venv
.\venv\Scripts\Activate.ps1

# Ejecutar (pedirá confirmación)
python scripts/reset_bd_cero.py

# Sin confirmación (útil en scripts/CI)
python scripts/reset_bd_cero.py --yes
```

## Qué hace

1. **Borra** todas las tablas de la base de datos
2. **Recrea** el esquema desde los modelos actuales
3. **Marca** alembic en `head`
4. **Crea** el usuario Ramon como ADMIN

## Credenciales por defecto

| Campo      | Valor                     |
|-----------|---------------------------|
| Nombre    | Ramon                     |
| Email     | admin@medinaautodiag.com  |
| Contraseña| Admin1234                 |

## Personalizar

Variables de entorno:

```env
RESET_ADMIN_NOMBRE=Ramon
RESET_ADMIN_EMAIL=admin@medinaautodiag.com
RESET_ADMIN_PASSWORD=Admin1234
```

## Requisitos

- `DATABASE_URL` o `DB_*` configurados (mismo que la API)
- Conectar a la misma base que usas en desarrollo/producción

## Aviso

**Solo ejecutar cuando no hay datos importantes.** Borra TODO irreversiblemente.
