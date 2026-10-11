# SOLVIS CRM — Fase 3: multi-cliente, actividades y front general

## Qué se agregó

- **Clientes (multi-tenant)**: app `tenants`. Cada usuario pertenece a un
  cliente y la API solo le muestra y le deja crear datos de ese cliente
  (`core/tenancy.py`). Los campos relacionados (empresa, contacto, etapa,
  usuario) tampoco aceptan registros de otro cliente.
- **Un front por cliente**: el cliente define en `frontend` qué carpeta de
  `frontends/` se abre al iniciar sesión. Ver `frontends/README.md`.
- **Conversión de leads**: `POST /api/leads/{id}/convert/` crea Empresa +
  Contacto (+ Oportunidad opcional), como el "Convertir" de Zoho CRM.
- **Actividades**: `api/notes/` y `api/tasks/`, colgadas de cualquier registro
  con `related_type` + `related_id`.
- **Inicio**: `GET /api/dashboard/` (números, pipeline, tareas, cierres del mes)
  y `GET /api/meta/` (opciones de los campos de selección).
- **Usuarios**: `GET /api/users/` lista los usuarios del cliente; el alta
  (`POST /api/users/`) ahora la hace un ADMINISTRADOR dentro de su cliente.
  El login devuelve también `user` con su `tenant`.
- **Front general Solvis** (`frontends/solvis/`): estructura tipo Zoho CRM
  (pestañas por módulo, filtros a la izquierda, ficha con listas
  relacionadas, tablero por etapa, búsqueda global) con la marca Solvis.

## Actualizar un entorno existente

```bash
python manage.py migrate
```

La migración `tenants.0002_default_tenant` crea el cliente **Solvis EAS**
(`slug=solvis`) y le asigna todo lo que ya existía. Las etapas del pipeline
ahora son por cliente: los clientes nuevos las reciben solas.

Datos de ejemplo para demos (en un cliente vacío):

```bash
python manage.py seed_demo_data --tenant demo
```

## Producción

`deploy/solvis-crm.service` (gunicorn en 127.0.0.1:8002) y
`deploy/nginx-crm.conf` (fronts + API). Variables nuevas en el entorno:
`CSRF_TRUSTED_ORIGINS` (ej: `https://crm.solvis.com.py`) y
`SECURE_SSL_REDIRECT` (`False` cuando Nginx ya redirige a https).

## Mejoras posteriores (estilo Zoho CRM)

- **Historial** de cada registro (`GET /api/timeline/`): altas, cambios de
  etapa/estado/propietario/monto, conversiones, notas y tareas.
- **Panel Solvis** (`/api/backoffice/`, solo `is_staff`): clientes, suspender,
  usuarios, contraseñas y cierre de sesiones. Un cliente suspendido queda
  afuera aunque tenga una sesión abierta.
- El **administrador de cada cliente** gestiona sus usuarios
  (`PATCH /api/users/{id}/`, `set-password/`, `logout/`) y cada usuario cambia
  su propia contraseña (`POST /api/users/me/password/`).
- Oportunidades: `closed_at` (fecha de cierre real) e `expected_revenue`
  (monto × probabilidad). Borrar una etapa en uso devuelve un error claro.
- Login con límite de intentos (15 por minuto por IP).
- Front: botones de WhatsApp y correo, acciones masivas, exportar a CSV,
  aviso de duplicados, clonar, vistos recientemente, contadores en el menú,
  atajo `/` para buscar y "Cambiar mi contraseña".

## Pruebas

```bash
python manage.py test tests --settings=config.settings.test
```
