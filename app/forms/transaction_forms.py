from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

class TransactionForm(FlaskForm):
    type = SelectField("Type", choices=[
        ("Income", "Income"),
        ("Expense", "Expense"),
        ("Debt Payment", "Debt Payment"),
        ("Credit Payment", "Credit Payment"),
    ])

    category = StringField("Category", validators=[DataRequired(), Length(max=120)])
    amount = FloatField("Amount", validators=[DataRequired()])
    description = TextAreaField("Description")
    submit = SubmitField("Save Transaction")
