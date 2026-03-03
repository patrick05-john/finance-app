from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.forms.auth_forms import RegisterForm, LoginForm
from app.models import User
from app import db
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()

        if existing_user:
            flash("Email is already registered.", "danger")
            return redirect(url_for("auth.register"))

        new_user = User(
            name=form.name.data,
            email=form.email.data,
        )
        new_user.set_password(form.password.data)

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # If user is already logged in, send to dashboard
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Logged in successfully.", "success")
            # Use 'next' parameter if available for better UX
            next_page = request.args.get('next')
            return redirect(next_page or url_for("dashboard.index"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    # UPDATED: Redirect to the public homepage instead of login page
    return redirect(url_for("index"))