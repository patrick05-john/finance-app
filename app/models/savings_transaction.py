from app import db
from datetime import datetime

class SavingsTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    savings_id = db.Column(db.Integer, db.ForeignKey("savings.id"), nullable=False)
    
    type = db.Column(db.String(20), nullable=False)  # 'deposit' or 'withdrawal'
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(255))
    
    user = db.relationship("User", backref="savings_transactions")
    savings = db.relationship("Savings", backref="transactions")
