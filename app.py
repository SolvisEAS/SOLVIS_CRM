"""
Punto de entrada de la aplicación.

Acá se arma la app de Flask, se conecta la base de datos, se registra
el login, y se define UN módulo del CRM por cada llamado a
create_crud_blueprint(). Para agregar un módulo nuevo en el futuro,
alcanza con sumar un bloque más acá abajo con sus campos y columnas.
"""
import os
from datetime import date

from flask import Flask, render_template, redirect, url_for
from flask_login import login_required, current_user

from extensions import db, login_manager
from crud import create_crud_blueprint
import auth
import models
from models import Company, Contact, Lead, Opportunity, Product, Activity, Delivery


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///crm.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    # ---- Empresas -----------------------------------------------------
    companies_bp = create_crud_blueprint(
        name="companies",
        model=Company,
        title="Empresas",
        fields=[
            {"name": "name", "label": "Nombre", "type": "text", "required": True},
            {"name": "industry", "label": "Rubro", "type": "text"},
            {"name": "phone", "label": "Teléfono", "type": "text"},
            {"name": "email", "label": "Email", "type": "email"},
            {"name": "address", "label": "Dirección", "type": "text"},
            {"name": "website", "label": "Sitio web", "type": "text"},
            {"name": "notes", "label": "Notas", "type": "textarea"},
        ],
        list_columns=[
            {"name": "name", "label": "Nombre"},
            {"name": "industry", "label": "Rubro"},
            {"name": "phone", "label": "Teléfono"},
            {"name": "email", "label": "Email"},
        ],
    )

    # ---- Contactos ------------------------------------------------------
    contacts_bp = create_crud_blueprint(
        name="contacts",
        model=Contact,
        title="Contactos",
        fields=[
            {"name": "first_name", "label": "Nombre", "type": "text", "required": True},
            {"name": "last_name", "label": "Apellido", "type": "text"},
            {"name": "email", "label": "Email", "type": "email"},
            {"name": "phone", "label": "Teléfono", "type": "text"},
            {"name": "position", "label": "Cargo", "type": "text"},
            {
                "name": "company_id",
                "label": "Empresa",
                "type": "select",
                "choices": lambda: [(c.id, c.name) for c in Company.query.order_by(Company.name)],
            },
            {"name": "notes", "label": "Notas", "type": "textarea"},
        ],
        list_columns=[
            {"name": "first_name", "label": "Nombre", "display": lambda c: c.full_name()},
            {"name": "email", "label": "Email"},
            {"name": "phone", "label": "Teléfono"},
            {
                "name": "company_id",
                "label": "Empresa",
                "display": lambda c: c.company.name if c.company else "",
            },
        ],
    )

    # ---- Leads / Posibles clientes ---------------------------------------
    leads_bp = create_crud_blueprint(
        name="leads",
        model=Lead,
        title="Leads",
        fields=[
            {"name": "name", "label": "Nombre", "type": "text", "required": True},
            {"name": "email", "label": "Email", "type": "email"},
            {"name": "phone", "label": "Teléfono", "type": "text"},
            {"name": "source", "label": "Origen", "type": "text"},
            {
                "name": "status",
                "label": "Estado",
                "type": "select",
                "choices": lambda: [(s, s) for s in Lead.STATUSES],
            },
            {"name": "notes", "label": "Notas", "type": "textarea"},
        ],
        list_columns=[
            {"name": "name", "label": "Nombre"},
            {"name": "email", "label": "Email"},
            {"name": "source", "label": "Origen"},
            {"name": "status", "label": "Estado"},
        ],
    )

    # ---- Oportunidades ----------------------------------------------------
    opportunities_bp = create_crud_blueprint(
        name="opportunities",
        model=Opportunity,
        title="Oportunidades",
        fields=[
            {"name": "name", "label": "Nombre", "type": "text", "required": True},
            {
                "name": "company_id",
                "label": "Empresa",
                "type": "select",
                "choices": lambda: [(c.id, c.name) for c in Company.query.order_by(Company.name)],
            },
            {
                "name": "contact_id",
                "label": "Contacto",
                "type": "select",
                "choices": lambda: [(c.id, c.full_name()) for c in Contact.query.all()],
            },
            {"name": "amount", "label": "Monto estimado", "type": "number"},
            {
                "name": "stage",
                "label": "Etapa",
                "type": "select",
                "choices": lambda: [(s, s) for s in Opportunity.STAGES],
            },
            {"name": "expected_close_date", "label": "Cierre estimado", "type": "date"},
            {"name": "notes", "label": "Notas", "type": "textarea"},
        ],
        list_columns=[
            {"name": "name", "label": "Nombre"},
            {
                "name": "company_id",
                "label": "Empresa",
                "display": lambda o: o.company.name if o.company else "",
            },
            {"name": "amount", "label": "Monto"},
            {"name": "stage", "label": "Etapa"},
        ],
    )

    # ---- Productos --------------------------------------------------------
    products_bp = create_crud_blueprint(
        name="products",
        model=Product,
        title="Productos",
        fields=[
            {"name": "name", "label": "Nombre", "type": "text", "required": True},
            {"name": "sku", "label": "SKU / Código", "type": "text"},
            {"name": "price", "label": "Precio", "type": "number"},
            {"name": "description", "label": "Descripción", "type": "textarea"},
        ],
        list_columns=[
            {"name": "name", "label": "Nombre"},
            {"name": "sku", "label": "SKU"},
            {"name": "price", "label": "Precio"},
        ],
    )

    # ---- Actividades (reuniones, tareas, recordatorios) --------------------
    activities_bp = create_crud_blueprint(
        name="activities",
        model=Activity,
        title="Actividades",
        fields=[
            {
                "name": "type",
                "label": "Tipo",
                "type": "select",
                "choices": lambda: [(t, t) for t in Activity.TYPES],
            },
            {"name": "title", "label": "Título", "type": "text", "required": True},
            {"name": "description", "label": "Descripción", "type": "textarea"},
            {"name": "due_date", "label": "Fecha límite", "type": "date"},
            {
                "name": "status",
                "label": "Estado",
                "type": "select",
                "choices": lambda: [(s, s) for s in Activity.STATUSES],
            },
            {
                "name": "lead_id",
                "label": "Lead relacionado",
                "type": "select",
                "choices": lambda: [(l.id, l.name) for l in Lead.query.all()],
            },
            {
                "name": "contact_id",
                "label": "Contacto relacionado",
                "type": "select",
                "choices": lambda: [(c.id, c.full_name()) for c in Contact.query.all()],
            },
            {
                "name": "opportunity_id",
                "label": "Oportunidad relacionada",
                "type": "select",
                "choices": lambda: [(o.id, o.name) for o in Opportunity.query.all()],
            },
        ],
        list_columns=[
            {"name": "type", "label": "Tipo"},
            {"name": "title", "label": "Título"},
            {"name": "due_date", "label": "Fecha límite"},
            {"name": "status", "label": "Estado"},
        ],
    )

    # ---- Seguimiento de Delivery --------------------------------------------
    deliveries_bp = create_crud_blueprint(
        name="deliveries",
        model=Delivery,
        title="Seguimiento Delivery",
        fields=[
            {
                "name": "opportunity_id",
                "label": "Oportunidad",
                "type": "select",
                "choices": lambda: [(o.id, o.name) for o in Opportunity.query.all()],
            },
            {
                "name": "product_id",
                "label": "Producto",
                "type": "select",
                "choices": lambda: [(p.id, p.name) for p in Product.query.all()],
            },
            {
                "name": "status",
                "label": "Estado",
                "type": "select",
                "choices": lambda: [(s, s) for s in Delivery.STATUSES],
            },
            {"name": "delivery_date", "label": "Fecha de entrega", "type": "date"},
            {"name": "notes", "label": "Notas", "type": "textarea"},
        ],
        list_columns=[
            {
                "name": "opportunity_id",
                "label": "Oportunidad",
                "display": lambda d: d.opportunity.name if d.opportunity else "",
            },
            {
                "name": "product_id",
                "label": "Producto",
                "display": lambda d: d.product.name if d.product else "",
            },
            {"name": "status", "label": "Estado"},
            {"name": "delivery_date", "label": "Entrega"},
        ],
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(companies_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(opportunities_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(deliveries_bp)

    @app.route("/")
    @login_required
    def index():
        stats = {
            "leads": Lead.query.count(),
            "contacts": Contact.query.count(),
            "companies": Company.query.count(),
            "opportunities": Opportunity.query.count(),
            "products": Product.query.count(),
            "activities": Activity.query.filter_by(status="Pendiente").count(),
            "deliveries": Delivery.query.filter(Delivery.status != "Entregado").count(),
        }
        return render_template("index.html", stats=stats)

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
