from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, Optional

# Profile update
class ProfileForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired()])
    submit = SubmitField("Save Profile")

# Password change
class PasswordChangeForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm New Password", validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField("Change Password")

# Notification & preference settings
class PreferencesForm(FlaskForm):
    notify_email = BooleanField("Email Notifications")
    notify_push = BooleanField("Push Notifications (future)")
    currency = SelectField("Currency", choices=[
        ("PHP", "Philippine Peso (PHP)"),
        ("USD", "US Dollar (USD)"),
        ("EUR", "Euro (EUR)")
    ])
    timezone = SelectField("Timezone", choices=[
        ("Asia/Manila", "Asia/Manila"),
        ("Asia/Kolkata", "Asia/Kolkata"),
        ("UTC", "UTC"),
        ("America/New_York", "America/New_York")
    ])
    submit = SubmitField("Save Preferences")

# Account deletion confirmation
class DeleteAccountForm(FlaskForm):
    password = PasswordField("Enter your password to confirm", validators=[DataRequired()])
    submit = SubmitField("Delete Account")
