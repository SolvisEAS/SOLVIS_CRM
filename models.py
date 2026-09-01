"""
Modelos de la base de datos (uno por tabla).

Cada clase acá es una tabla en PostgreSQL/SQLite. SQLAlchemy se encarga
de traducir esto a SQL por nosotros.
"""
from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(UserMixin, db.Model):
    """Usuario que puede iniciar sesión en el CRM."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.email}>"


class Company(db.Model):
    """Empresas (clientes, prospectos, proveedores, etc.)."""
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    industry = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    website = db.Column(db.String(150))
    notes = db.Column(db.Text)

    contacts = db.relationship("Contact", backref="company", lazy=True)
    opportunities = db.relationship("Opportunity", backref="company", lazy=True)

    def __repr__(self):
        return f"<Company {self.name}>"


class Contact(db.Model):
    """Personas de contacto, normalmente asociadas a una Empresa."""
    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    position = db.Column(db.String(120))
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"))
    notes = db.Column(db.Text)

    def full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()

    def __repr__(self):
        return f"<Contact {self.full_name()}>"


class Lead(db.Model):
    """Posibles clientes que todavía no fueron calificados/convertidos."""
    __tablename__ = "leads"

    STATUSES = ["Nuevo", "Contactado", "Calificado", "Descartado"]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    source = db.Column(db.String(120))  # de dónde vino: web, referido, feria, etc.
    status = db.Column(db.String(30), default="Nuevo")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Lead {self.name}>"


class Opportunity(db.Model):
    """Oportunidades de venta ligadas a una Empresa/Contacto."""
    __tablename__ = "opportunities"

    STAGES = ["Prospección", "Propuesta", "Negociación", "Ganada", "Perdida"]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"))
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"))
    amount = db.Column(db.Float, default=0)
    stage = db.Column(db.String(30), default="Prospección")
    expected_close_date = db.Column(db.Date)
    notes = db.Column(db.Text)

    contact = db.relationship("Contact")

    def __repr__(self):
        return f"<Opportunity {self.name}>"


class Product(db.Model):
    """Catálogo de productos/servicios que se pueden vender."""
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    sku = db.Column(db.String(60))
    price = db.Column(db.Float, default=0)
    description = db.Column(db.Text)

    def __repr__(self):
        return f"<Product {self.name}>"


class Activity(db.Model):
    """Reuniones, tareas y recordatorios, opcionalmente ligados a un
    Lead, Contacto u Oportunidad."""
    __tablename__ = "activities"

    TYPES = ["Reunión", "Tarea", "Llamada", "Recordatorio"]
    STATUSES = ["Pendiente", "Completada"]

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(30), default="Tarea")
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(30), default="Pendiente")

    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"))
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"))
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunities.id"))

    lead = db.relationship("Lead")
    contact = db.relationship("Contact")
    opportunity = db.relationship("Opportunity")

    def __repr__(self):
        return f"<Activity {self.title}>"


class Delivery(db.Model):
    """Seguimiento de entrega (delivery) de un producto vendido en una
    Oportunidad ganada."""
    __tablename__ = "deliveries"

    STATUSES = ["Pendiente", "En proceso", "Entregado", "Cancelado"]

    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunities.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    status = db.Column(db.String(30), default="Pendiente")
    delivery_date = db.Column(db.Date)
    notes = db.Column(db.Text)

    opportunity = db.relationship("Opportunity")
    product = db.relationship("Product")

    def __repr__(self):
        return f"<Delivery #{self.id}>"
