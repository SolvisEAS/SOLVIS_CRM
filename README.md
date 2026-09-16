# SOLVIS CRM — Fase 1: Núcleo del proyecto

Esta es la primera fase de la migración de SOLVIS CRM (Flask) a Django.
Incluye únicamente lo que el documento de arquitectura define como
**núcleo**: proyecto Django, configuración por entornos, PostgreSQL,
modelo de usuario personalizado, autenticación JWT y permisos base.

Todavía **no** incluye Empresas, Contactos, Leads, Oportunidades, etc.
— eso es la Fase 2.

## 1. Requisitos previos

- Python 3.10+
- Docker y Docker Compose (para PostgreSQL)

## 2. Puesta en marcha (paso a paso)

### 2.1 Levantar PostgreSQL

```bash
docker compose up -d
```

Verificá que el contenedor está sano:

```bash
docker compose ps
# solvis_crm_db debe aparecer como "healthy"
```

### 2.2 Crear entorno virtual e instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements/development.txt
```

### 2.3 Configurar variables de entorno

```bash
cp .env.example .env
```

Editá `.env` y como mínimo cambiá `DJANGO_SECRET_KEY` por un valor
aleatorio propio. Podés generar uno con:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 2.4 Aplicar migraciones

```bash
python manage.py makemigrations users
python manage.py migrate
```

### 2.5 Crear un superusuario

```bash
python manage.py createsuperuser
```

### 2.6 Levantar el servidor

```bash
python manage.py runserver
```

## 3. Checklist de verificación de la Fase 1

No sigas a la Fase 2 hasta confirmar cada uno de estos puntos:

- [ ] **Docker/Postgres**: `docker compose ps` muestra `solvis_crm_db` como `healthy`.
- [ ] **Migraciones**: `python manage.py migrate` corre sin errores y crea las tablas (incluida `users_user`).
- [ ] **Admin de Django**: entrando a `http://127.0.0.1:8000/admin/` podés loguearte con el superusuario y ver el modelo "Usuarios" con el campo `role`.
- [ ] **Registro de usuario** (endpoint público):

  ```bash
  curl -X POST http://127.0.0.1:8000/api/users/register/ \
    -H "Content-Type: application/json" \
    -d '{"username":"jperez","email":"jperez@solvis.com","password":"unaClaveSegura123","first_name":"Juan","last_name":"Perez"}'
  ```

  Debe devolver `201 Created` con los datos del usuario (sin la contraseña).

- [ ] **Login JWT**:

  ```bash
  curl -X POST http://127.0.0.1:8000/api/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"username":"jperez","password":"unaClaveSegura123"}'
  ```

  Debe devolver un JSON con `access` y `refresh`.

- [ ] **Endpoint protegido `/me/`**:

  ```bash
  curl http://127.0.0.1:8000/api/users/me/ \
    -H "Authorization: Bearer <PEGAR_ACCESS_TOKEN_ACA>"
  ```

  Debe devolver los datos del usuario autenticado. Sin el header
  `Authorization`, debe devolver `401 Unauthorized`.

- [ ] **Refresh token**:

  ```bash
  curl -X POST http://127.0.0.1:8000/api/auth/refresh/ \
    -H "Content-Type: application/json" \
    -d '{"refresh":"<PEGAR_REFRESH_TOKEN_ACA>"}'
  ```

  Debe devolver un nuevo `access` token.

- [ ] **Logout (blacklist)**:

  ```bash
  curl -X POST http://127.0.0.1:8000/api/auth/logout/ \
    -H "Content-Type: application/json" \
    -d '{"refresh":"<PEGAR_REFRESH_TOKEN_ACA>"}'
  ```

  Debe devolver `200`. Un intento posterior de usar ese mismo refresh
  token para pedir un nuevo access token debe fallar.

## 4. Qué se decidió y por qué

- **Modelo de usuario personalizado desde el día 1**: se hereda de
  `AbstractUser` y se agrega `role`. Cambiar `AUTH_USER_MODEL` después
  de la primera migración es muy costoso en Django, por eso se resuelve
  ahora aunque los permisos granulares por módulo vengan en Fase 2/3.
- **Configuración por entornos** (`base.py` / `development.py` /
  `production.py`): siguiendo exactamente la estructura del documento,
  con `python-decouple` para leer variables de entorno.
- **PostgreSQL vía Docker** en desarrollo, para que el entorno local
  sea idéntico al de producción desde el principio.
- **JWT con `djangorestframework-simplejwt`**, incluyendo blacklist de
  refresh tokens para permitir un logout real.
- **Permisos base** (`core/permissions.py`): están las clases para
  `ADMINISTRADOR` y `GERENTE`, pero todavía no se aplican a ningún
  endpoint de negocio porque esos módulos no existen aún. Se van a
  usar a partir de la Fase 2.

## 5. Siguiente paso

Una vez que confirmes que todos los puntos de la checklist funcionan
en tu entorno, avisame y seguimos con la **Fase 2 — CRM básico**
(Empresas, Contactos, Leads, Oportunidades, Etapas del pipeline).
