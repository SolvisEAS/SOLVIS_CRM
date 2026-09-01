"""
Objetos compartidos de Flask (extensiones).

Los separamos en su propio archivo para evitar "import circular":
app.py, models.py y las rutas necesitan todos acceder a `db` y a
`login_manager`, pero no deben depender unos de otros.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor iniciá sesión para continuar."
login_manager.login_message_category = "warning"
