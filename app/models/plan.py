from app import db
from datetime import datetime

class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    plan_type = db.Column(db.String(50), nullable=False)  # 'Income' or 'Expense'
    date = db.Column(db.Date, nullable=False)
    
    # --- NEW RECURRING FEATURES ---
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_day = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
