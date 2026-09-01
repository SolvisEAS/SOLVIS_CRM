"""
Generador genérico de pantallas CRUD (Crear, Leer, Actualizar, Borrar).

En vez de escribir 7 veces casi el mismo código (una lista + un
formulario por cada módulo: Leads, Contactos, Empresas, Oportunidades,
Productos, Actividades, Delivery), armamos UNA sola función que arma
un Blueprint de Flask completo a partir de:

  - el modelo de SQLAlchemy (por ejemplo, models.Contact)
  - la lista de campos que tiene el formulario
  - las columnas que se muestran en la tabla de listado

Así, agregar un módulo nuevo el día de mañana es simplemente definir
sus campos y llamar a create_crud_blueprint() una vez más — no hay
que copiar y pegar rutas ni plantillas HTML nuevas.
"""
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from extensions import db


def _parse_value(field, raw_value):
    """Convierte el texto que llega del formulario HTML al tipo de dato
    correcto (número, fecha, etc.) antes de guardarlo en la base."""
    if raw_value in (None, ""):
        return None
    if field["type"] == "number":
        try:
            return float(raw_value)
        except ValueError:
            return None
    if field["type"] == "date":
        try:
            return datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return raw_value


def create_crud_blueprint(name, model, fields, list_columns, title):
    """
    name: identificador corto usado en las URLs, ej. "contacts"
    model: la clase del modelo, ej. models.Contact
    fields: lista de dicts describiendo cada campo del formulario
    list_columns: lista de dicts describiendo cada columna de la tabla
    title: título legible del módulo, ej. "Contactos"
    """
    bp = Blueprint(name, __name__, url_prefix=f"/{name}")

    def _resolve_choices():
        # Para los campos tipo "select" (por ejemplo, elegir una Empresa
        # dentro del formulario de Contacto), calculamos las opciones
        # justo antes de mostrar el formulario, para que reflejen los
        # datos más recientes.
        for field in fields:
            if field["type"] == "select":
                field["_choices"] = field["choices"]()

    @bp.route("/")
    @login_required
    def list_view():
        items = model.query.order_by(model.id.desc()).all()
        rows = []
        for item in items:
            row = []
            for col in list_columns:
                if "display" in col:
                    value = col["display"](item)
                else:
                    value = getattr(item, col["name"])
                row.append(value if value not in (None, "") else "—")
            rows.append({"id": item.id, "cells": row})
        headers = [col["label"] for col in list_columns]
        return render_template(
            "list.html",
            title=title,
            module=name,
            headers=headers,
            rows=rows,
        )

    @bp.route("/new", methods=["GET", "POST"])
    @login_required
    def create_view():
        _resolve_choices()
        if request.method == "POST":
            item = model()
            for field in fields:
                value = _parse_value(field, request.form.get(field["name"]))
                setattr(item, field["name"], value)
            db.session.add(item)
            db.session.commit()
            flash(f"{title}: registro creado con éxito.", "success")
            return redirect(url_for(f"{name}.list_view"))
        return render_template(
            "form.html", title=title, module=name, fields=fields, item=None
        )

    @bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_view(item_id):
        item = model.query.get_or_404(item_id)
        _resolve_choices()
        if request.method == "POST":
            for field in fields:
                value = _parse_value(field, request.form.get(field["name"]))
                setattr(item, field["name"], value)
            db.session.commit()
            flash(f"{title}: registro actualizado.", "success")
            return redirect(url_for(f"{name}.list_view"))
        return render_template(
            "form.html", title=title, module=name, fields=fields, item=item
        )

    @bp.route("/<int:item_id>/delete", methods=["POST"])
    @login_required
    def delete_view(item_id):
        item = model.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        flash(f"{title}: registro eliminado.", "info")
        return redirect(url_for(f"{name}.list_view"))

    return bp
