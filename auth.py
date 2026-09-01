"""
Registro, login y logout de usuarios (email + contraseña).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required

from extensions import db
from models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if not name or not email or not password:
            error = "Completá nombre, email y contraseña."
        elif password != confirm:
            error = "Las contraseñas no coinciden."
        elif len(password) < 6:
            error = "La contraseña debe tener al menos 6 caracteres."
        elif User.query.filter_by(email=email).first():
            error = "Ya existe un usuario registrado con ese email."

        if error:
            flash(error, "danger")
            return render_template("auth/register.html", name=name, email=email)

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Cuenta creada con éxito. Ya podés iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"¡Bienvenido, {user.name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

        flash("Email o contraseña incorrectos.", "danger")
        return render_template("auth/login.html", email=email)

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))
