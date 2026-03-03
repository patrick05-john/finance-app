from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, SelectField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import date

class DebtForm(FlaskForm):
    debt_type = SelectField('Type', choices=[
        ('Credit Card', 'Credit Card'),
        ('Loan', 'Loan'),
        ('Debt', 'Debt'),
        ('Others', 'Others')
    ], validators=[DataRequired()])

    name = StringField('Account Name', validators=[DataRequired()])
    limit_amount = FloatField('Credit Limit', validators=[Optional()])
    balance = FloatField('Current Balance', validators=[DataRequired()])
    minimum_payment = FloatField('Minimum Payment', validators=[DataRequired()])

    # NOW GLOBAL for all debt types
    monthly_due_date = IntegerField('Monthly Due Day (1-31)', validators=[DataRequired(), NumberRange(min=1, max=31)])

    # Loan-specific fields
    loan_start_date = DateField('Loan Start Date', validators=[Optional()])
    loan_end_date = DateField('Loan End Date', validators=[Optional()])


class PaymentForm(FlaskForm):
    amount = FloatField('Payment Amount', validators=[DataRequired()])
    funding_source = SelectField('Funding Source', choices=[
        ('balance', 'Main Balance')
    ], validators=[DataRequired()])
    income_source = SelectField('Income Source', choices=[('0', 'None')], validators=[Optional()])
