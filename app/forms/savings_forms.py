from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField
from wtforms.validators import DataRequired

class SavingsGoalForm(FlaskForm):
    goal_name = StringField("Goal Name", validators=[DataRequired()])
    target_amount = FloatField("Target Amount", validators=[DataRequired()])
    submit = SubmitField("Create Savings Goal")


class SavingsDepositForm(FlaskForm):
    deposit_amount = FloatField("Deposit Amount", validators=[DataRequired()])
    submit = SubmitField("Deposit")
