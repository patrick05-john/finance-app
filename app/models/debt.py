from app import db
from datetime import datetime, date
import calendar

class Debt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    debt_type = db.Column(db.String(50), nullable=False)  # Debt or Credit Card
    name = db.Column(db.String(120), nullable=False)

    limit_amount = db.Column(db.Float, nullable=True)     # For credit cards
    balance = db.Column(db.Float, default=0)

    minimum_payment = db.Column(db.Float, default=0)
    due_date = db.Column(db.Date, nullable=False)         # Kept to prevent DB constraint errors

    # Loan-specific fields
    loan_start_date = db.Column(db.Date, nullable=True)   # For loans only
    loan_end_date = db.Column(db.Date, nullable=True)     # For loans only
    monthly_due_date = db.Column(db.Integer, nullable=True)  # Day of month (1-31) - NOW GLOBAL

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="debts")

    @property
    def due_status(self):
        if not self.monthly_due_date:
            return None
        
        today = date.today()
        
        # Helper to safely get a date, capping the day to the month's max days
        def get_valid_date(y, m, d):
            last_day = calendar.monthrange(y, m)[1]
            return date(y, m, min(d, last_day))

        this_month_due = get_valid_date(today.year, today.month, self.monthly_due_date)
        delta = (this_month_due - today).days

        # If it's more than 5 days PAST the due date, calculate based on NEXT month's due date
        if delta < -5:
            m = today.month + 1
            y = today.year
            if m > 12:
                m = 1
                y += 1
            next_due = get_valid_date(y, m, self.monthly_due_date)
            delta_next = (next_due - today).days
            
            if delta_next <= 5:
                return {"status": "DUE SOON", "days": delta_next, "date": next_due}
            return {"status": "SAFE", "days": delta_next, "date": next_due}

        # Handle Current Month Status
        if delta < 0:
            return {"status": "OVERDUE", "days": abs(delta), "date": this_month_due}
        elif delta == 0:
            return {"status": "DUE TODAY", "days": 0, "date": this_month_due}
        elif delta <= 5:
            return {"status": "DUE SOON", "days": delta, "date": this_month_due}
        else:
            return {"status": "SAFE", "days": delta, "date": this_month_due}

    @property
    def is_loan(self):
        return self.debt_type == "Loan"

    @property
    def loan_duration_months(self):
        if self.is_loan and self.loan_start_date and self.loan_end_date:
            delta = self.loan_end_date - self.loan_start_date
            return round(delta.days / 30.44)
        return 0
