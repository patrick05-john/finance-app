from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.forms.settings_forms import ProfileForm, PasswordChangeForm, PreferencesForm, DeleteAccountForm
from app import db
from app.models import User
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

def current_user():
    if "user_id" not in session:
        return None
    return User.query.get(session["user_id"])

@settings_bp.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
        
    user = current_user()
    
    # Initialize all forms
    profile_form = ProfileForm(obj=user)
    password_form = PasswordChangeForm()
    preferences_form = PreferencesForm(obj=user)
    delete_form = DeleteAccountForm()
    
    # Check which form was submitted based on a hidden field or the submit button name
    if request.method == "POST":
        if "update_profile" in request.form and profile_form.validate_on_submit():
            user.name = profile_form.name.data
            user.email = profile_form.email.data
            try:
                db.session.commit()
                session["user_name"] = user.name
                flash("Profile updated successfully.", "success")
            except IntegrityError:
                db.session.rollback()
                flash("This email is already in use.", "danger")
            return redirect(url_for("settings.index"))

        elif "change_password" in request.form and password_form.validate_on_submit():
            if not user.check_password(password_form.current_password.data):
                flash("Current password is incorrect.", "danger")
            else:
                user.set_password(password_form.new_password.data)
                db.session.commit()
                flash("Password changed successfully.", "success")
            return redirect(url_for("settings.index"))

        elif "save_preferences" in request.form and preferences_form.validate_on_submit():
            user.notify_email = bool(preferences_form.notify_email.data)
            user.notify_push = bool(preferences_form.notify_push.data)
            user.currency = preferences_form.currency.data
            user.timezone = preferences_form.timezone.data
            db.session.commit()
            flash("Preferences saved successfully.", "success")
            return redirect(url_for("settings.index"))

        elif "delete_account" in request.form and delete_form.validate_on_submit():
            if not user.check_password(delete_form.password.data):
                flash("Password incorrect. Account not deleted.", "danger")
            else:
                db.session.delete(user)
                db.session.commit()
                session.clear()
                flash("Your account has been deleted.", "info")
                return redirect(url_for("auth.register"))

    return render_template(
        "settings/index.html", 
        user=user,
        profile_form=profile_form,
        password_form=password_form,
        preferences_form=preferences_form,
        delete_form=delete_form
    )

# Fallback routes for old cached links
@settings_bp.route("/profile")
@settings_bp.route("/change-password")
@settings_bp.route("/preferences")
@settings_bp.route("/delete-account")
def old_routes_fallback():
    return redirect(url_for("settings.index"))
