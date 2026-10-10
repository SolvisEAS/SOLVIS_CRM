# Fronts de SOLVIS CRM

Un solo back (la API Django en `/api/`) y un front por cliente.

```
frontends/
├── index.html      → puerta de entrada: abre el front del usuario con sesión, o "solvis"
├── shared/api.js   → cliente de la API común a todos los fronts (login, tokens, redirección)
└── solvis/         → front general de Solvis (también se usa para las demos)
```

## Cómo decide qué front abrir

Cada usuario pertenece a un **cliente** (`Tenant`). El cliente tiene el campo
`frontend`, que es el nombre de una carpeta de acá. Al iniciar sesión, la API
devuelve `user.tenant.frontend`; si el usuario está en otro front, se lo
redirige a `/<frontend>/`. Los datos ya vienen filtrados por cliente desde la
API, así que un cliente nunca ve datos de otro.

## Crear el front de un cliente nuevo

1. Copiar la carpeta: `cp -r frontends/solvis frontends/<cliente>`.
2. En `frontends/<cliente>/js/app.js` cambiar `const FRONTEND = "solvis"` por `"<cliente>"`.
3. Cambiar logo (`img/`), colores (`css/app.css`, variables `--primary` y `--accent`)
   y textos del login. Los módulos y campos se ajustan en `js/modules.js`.
4. En el admin de Django (`/admin/`), crear el cliente con `frontend = <cliente>`
   y sus usuarios.

Si el cliente solo necesita otros colores o logo, no hace falta copiar nada:
alcanza con cargar `primary_color`, `accent_color` y `logo_url` en el cliente y
dejarle `frontend = solvis`.

## Tecnología

HTML, CSS y JavaScript sin compilación (módulos ES nativos). Se publican tal
cual con Nginx; no hace falta Node ni build.
