from app import db
from datetime import datetime

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    source = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", backref="incomes")
