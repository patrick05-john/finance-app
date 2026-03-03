from app import db
from datetime import datetime

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # type: Income, Expense, Debt Payment, Credit Payment
    type = db.Column(db.String(50), nullable=False)

    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(120))
    description = db.Column(db.String(255))
    date = db.Column(db.DateTime, default=datetime.utcnow)

    # budget_id (optional) - links transaction to a specific budget
    budget_id = db.Column(db.Integer, db.ForeignKey("budget.id"), nullable=True)

    # deduct_from (optional) - where to deduct expense from
    deduct_from = db.Column(db.String(50), nullable=True)

    user = db.relationship("User", backref="transactions")
    budget = db.relationship("Budget", backref="transactions")




