from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from datetime import date

TRANSACTION_CATEGORIES = [
    ("", "-- Select a Category --"),
    ("Groceries", "Groceries"),
    ("Foods", "Foods"),
    ("Rent/Mortgage", "Rent/Mortgage"),
    ("Utilities", "Utilities (Electric, Water, etc.)"),
    ("Transport", "Transportation"),
    ("Salary", "Salary/Wages"),
    ("Investments", "Investments"),
    ("Debt Repayment", "Debt Repayment"),
    ("Entertainment", "Entertainment"),
    ("Health", "Health & Wellness"),
    ("Electronic Devices", "Electronic Devices (Phone, Tablet, Laptop, etc.)"),
    ("Other", "Other"),
]

DEDUCT_OPTIONS = [
    ("", "-- Select Funding Source --"),
    ("income", "Main Income Balance"),
    ("budget", "Active Budget Allocation"),
    ("savings", "Savings Goal"),
    ("debt", "Add Credit/Debt Account"),
]

class TransactionForm(FlaskForm):
    type = SelectField("Type", choices=[
        ("", "-- Select Type --"),
        ("Income", "Income"),
        ("Expense", "Expense"),
        ("Debt Payment", "Debt Payment"),
        ("Credit Payment", "Credit Payment"),
    ], validators=[DataRequired()])

    category = SelectField("Category", choices=TRANSACTION_CATEGORIES, validators=[DataRequired()])

    # NEW: Optional custom category field
    custom_category = StringField("Specify Other Category", validators=[Optional(), Length(max=100)])

    amount = FloatField("Amount (P)", validators=[DataRequired()])
    date = DateField("Date", default=date.today, validators=[DataRequired()])
    deduct_from = SelectField("Funding Source", choices=DEDUCT_OPTIONS, validators=[Optional()])
    description = TextAreaField("Description", validators=[Length(max=255)])
    submit = SubmitField("Save Transaction")

class EditTransactionForm(TransactionForm):
    pass
