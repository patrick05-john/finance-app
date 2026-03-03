from flask_wtf import FlaskForm
from wtforms import FloatField, StringField, SubmitField
from wtforms.validators import DataRequired

class IncomeForm(FlaskForm):
    amount = FloatField("Income Amount", validators=[DataRequired()])
    source = StringField("Source (optional)")
    submit = SubmitField("Add Income")
