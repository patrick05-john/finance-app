from app import db
from datetime import datetime, date


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    funding_source = db.Column(db.String(50), default="income")  # NEW: income, savings, credit, others
    description = db.Column(db.String(255))

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="budgets")

    def is_active(self):
        today = date.today()
        return self.start_date <= today <= self.end_date
