# CRM Roancom — versión inicial

CRM básico hecho con Python (Flask). Incluye login por email/contraseña y 7 módulos: Leads, Contactos, Empresas, Oportunidades, Productos, Actividades y Seguimiento de Delivery.

## Estructura del proyecto

```
crm-app/
  app.py          -> arma la app y define los 7 módulos (campos y columnas de cada uno)
  extensions.py   -> objetos compartidos (base de datos, login)
  models.py       -> las tablas de la base de datos
  auth.py         -> registro / login / logout
  crud.py         -> el "motor" genérico que arma listar/crear/editar/borrar para cualquier módulo
  templates/      -> las páginas HTML (usa Bootstrap por CDN, no hay que instalar nada aparte)
  requirements.txt
```

## Cómo correrlo en su computadora (desarrollo local)

1. Necesitan Python 3.10 o superior instalado.
2. Abran una terminal dentro de la carpeta `crm-app` y creen un entorno virtual:

   ```
   python3 -m venv venv
   ```

   En Windows: `python -m venv venv`

3. Actívenlo:

   - Windows (PowerShell): `venv\Scripts\Activate.ps1`
   - Mac/Linux: `source venv/bin/activate`

4. Instalen las dependencias:

   ```
   pip install -r requirements.txt
   ```

5. Corran la aplicación:

   ```
   python app.py
   ```

6. Abran el navegador en `http://127.0.0.1:5000` — la primera vez los va a mandar a la pantalla de login. Hagan clic en "Registrate" para crear el primer usuario.

Por defecto usa una base de datos SQLite local (un archivo `crm.db` que se crea solo en la carpeta). No hace falta instalar PostgreSQL para probarlo en la computadora.

## Cómo agregar un módulo nuevo el día de mañana

Todos los módulos (Leads, Contactos, etc.) se generan con la misma función `create_crud_blueprint()` en `app.py`. Para agregar uno nuevo:

1. Agregar el modelo (la tabla) en `models.py`.
2. Copiar uno de los bloques existentes en `app.py` (por ejemplo el de "Productos") y cambiar el nombre, el modelo y los campos.
3. Agregar `app.register_blueprint(mi_nuevo_bp)` junto a los demás.
4. Agregarlo al menú de navegación en `templates/base.html`.

No hace falta tocar ni `crud.py` ni las plantillas `list.html`/`form.html` — esas son genéricas y sirven para cualquier módulo nuevo.

## Trabajar de a dos con Git/GitHub

1. Uno de los dos crea un repositorio nuevo en GitHub (privado, ya que va a tener el código de la empresa).
2. Suben este proyecto tal cual está (excepto la carpeta `venv/` y el archivo `crm.db`, que no deben subirse — ya viene un `.gitignore` preparado para esto).
3. El otro clona el repositorio y sigue los pasos de "Cómo correrlo en su computadora" de arriba.
4. Trabajen con ramas (`git checkout -b nombre-de-la-funcionalidad`) y Pull Requests para no pisarse el código.

## Próximo paso: desplegarlo en el servidor de UpCloud

Esto lo vamos a hacer juntos más adelante, una vez que el CRM esté andando bien en local y probado por los dos. La idea general (ya la charlamos):

- Usar la misma base PostgreSQL que ya está instalada en el servidor (creando una base de datos nueva, separada de la de Odoo).
- Correr esta app con Gunicorn (un servidor de producción para Flask) en un puerto distinto al de Odoo (por ejemplo, el 5000).
- Armar un servicio de systemd, igual a como hicimos con Odoo, para que quede siempre encendido.
- Configurar Nginx como "portero" para que Odoo y el CRM convivan prolijos en el mismo servidor.
