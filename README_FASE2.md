# SOLVIS CRM — Fase 2: CRM básico

Se agregaron los 4 módulos centrales del CRM (punto 16 del documento):
**Empresas, Contactos, Leads, Oportunidades y Etapas del pipeline.**

Todavía **no** incluye: conversión de Lead a Oportunidad, actividades,
historial de cambios (eso es Fase 3), ni dashboard/kanban/vistas (Fase 4).

## 1. Actualizar tu entorno existente

Si ya tenías la Fase 1 corriendo, no hace falta reinstalar nada — no
se agregaron dependencias nuevas. Solo hay que migrar los modelos
nuevos:

```bash
source venv/bin/activate   # si no está activo
python manage.py makemigrations companies contacts opportunities leads
python manage.py migrate
```

### Sembrar las etapas del pipeline por defecto

El punto 9 del documento pide que las etapas no estén hardcodeadas.
Por eso, en vez de venir precargadas por una migración, se cargan con
un comando (así podés modificarlas o correr esto de nuevo si las
borraste):

```bash
python manage.py seed_pipeline_stages
```

Esto crea: Nueva, Calificada, Propuesta, Negociación, Ganada, Perdida.

### Levantar el servidor

```bash
python manage.py runserver
```

## 2. Endpoints nuevos

Todos requieren el header `Authorization: Bearer <access_token>`
(usá el login de la Fase 1 para conseguirlo).

| Recurso            | URL base                     |
|---------------------|-------------------------------|
| Empresas            | `/api/companies/`            |
| Contactos            | `/api/contacts/`              |
| Oportunidades        | `/api/opportunities/`         |
| Etapas del pipeline  | `/api/pipeline-stages/`       |
| Leads                | `/api/leads/`                  |

Cada uno soporta `GET` (listar), `POST` (crear), `GET /{id}/`,
`PUT`/`PATCH /{id}/`, `DELETE /{id}/` — CRUD completo, con búsqueda
(`?search=`), filtros por campo (ej: `?company=1`) y orden
(`?ordering=-created_at`).

## 3. Checklist de verificación de la Fase 2

No sigas a la Fase 3 hasta confirmar cada uno de estos puntos.
Guardá el `access` token de un login previo en una variable para
que los comandos sean más cómodos:

```bash
export TOKEN="<pegar_access_token_aca>"
```

- [ ] **Migraciones**: `makemigrations` + `migrate` corren sin errores.
- [ ] **Seed de etapas**: `python manage.py seed_pipeline_stages` reporta "6 etapas nuevas creadas".
- [ ] **Ver etapas del pipeline**:

  ```bash
  curl http://127.0.0.1:8000/api/pipeline-stages/ -H "Authorization: Bearer $TOKEN"
  ```

  Debe devolver una lista con las 6 etapas, ordenadas por `sequence`.

- [ ] **Crear una empresa**:

  ```bash
  curl -X POST http://127.0.0.1:8000/api/companies/ \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"name":"Acme SA","email":"contacto@acme.com","city":"Asunción","country":"Paraguay"}'
  ```

  Anotá el `id` que devuelve — lo vas a necesitar en los pasos siguientes.

- [ ] **Crear un contacto** vinculado a esa empresa:

  ```bash
  curl -X POST http://127.0.0.1:8000/api/contacts/ \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"first_name":"Ana","last_name":"Gómez","email":"ana@acme.com","company":<ID_EMPRESA>}'
  ```

  La respuesta debe incluir `"company_name": "Acme SA"`.

- [ ] **Crear una oportunidad** vinculada a esa empresa y a la etapa "Nueva":

  ```bash
  curl -X POST http://127.0.0.1:8000/api/opportunities/ \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"name":"Venta anual Acme","company":<ID_EMPRESA>,"contact":<ID_CONTACTO>,"amount":"15000.00","stage":<ID_ETAPA_NUEVA>}'
  ```

  La respuesta debe incluir `"stage_name": "Nueva"` y `"company_name": "Acme SA"`.

- [ ] **Filtrar oportunidades por empresa**:

  ```bash
  curl "http://127.0.0.1:8000/api/opportunities/?company=<ID_EMPRESA>" -H "Authorization: Bearer $TOKEN"
  ```

- [ ] **Crear un lead** (independiente, sin relaciones formales todavía):

  ```bash
  curl -X POST http://127.0.0.1:8000/api/leads/ \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"title":"Interesado en demo","name":"Carlos Ruiz","email":"carlos@prospecto.com","company":"Prospecto SRL","source":"FORMULARIO"}'
  ```

- [ ] **Filtrar leads por estado**:

  ```bash
  curl "http://127.0.0.1:8000/api/leads/?status=NUEVO" -H "Authorization: Bearer $TOKEN"
  ```

- [ ] **Admin de Django**: en `http://127.0.0.1:8000/admin/` ves las secciones "Empresas", "Contactos", "Oportunidades", "Etapas del pipeline" y "Leads", cada una con sus registros de prueba.

- [ ] **Eliminar un registro** (ej: el contacto de prueba) y confirmar `204 No Content`.

## 4. Qué se decidió y por qué

- **`Lead.company` es texto libre, no una relación**: en esta etapa
  el prospecto puede no tener todavía una `Company` real en el
  sistema. La conversión formal (Lead → Contacto/Empresa/Oportunidad)
  es lógica de negocio de la Fase 3, no de esta.
- **`PipelineStage` es un modelo propio, sembrado por comando** y no
  hardcodeado ni cargado por migración de datos — así se puede
  editar libremente desde el admin o la API sin tocar código,
  cumpliendo el punto 9 del documento.
- **`stage` en Opportunity usa `on_delete=PROTECT`**: no se puede
  borrar una etapa que tiene oportunidades activas, para no perder
  la trazabilidad del pipeline.
- **Owner/assigned_to se autocompletan** con el usuario autenticado
  si no se especifican al crear, para que la API sea usable desde
  ya sin tener que mandar siempre ese campo.

## 5. Siguiente paso

Una vez que confirmes que todos los puntos de la checklist funcionan,
seguimos con la **Fase 3 — Gestión comercial**: Actividades,
conversión de Leads, asignación de oportunidades e historial de
cambios (auditoría). Esa fase es también donde vamos a empezar a
diseñar el terreno para el motor de reglas de flujo/automatizaciones
que mencionaste (Zoho-style).
