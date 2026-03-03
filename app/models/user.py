from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Financial Fields
    total_balance = db.Column(db.Float, default=0.0)  # ✅ ADDED: Main financial balance

    # Preferences
    notify_email = db.Column(db.Boolean, default=True)   # email alerts
    notify_push = db.Column(db.Boolean, default=False)   # future use
    currency = db.Column(db.String(10), default="PHP")
    timezone = db.Column(db.String(50), default="Asia/Manila")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
