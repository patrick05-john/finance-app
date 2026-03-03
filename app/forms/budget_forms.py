from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length

# Define funding source options based on your transactions logic
FUNDING_OPTIONS = [
    ("income", "Main Income Balance (Default)"),
    ("savings", "Savings Goal"),
    ("credit", "Credit/Debt Account (e.g., Credit Card)"),
]

class BudgetForm(FlaskForm):
    name = StringField("Budget Name", validators=[DataRequired(), Length(max=120)])
    amount = FloatField("Total Budget Amount (₱)", validators=[DataRequired()])
    
    funding_source = SelectField(
        "Funding Source", 
        choices=FUNDING_OPTIONS, 
        validators=[DataRequired()],
        description="Choose where funds for this budget will be deducted from."
    )
    
    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Length(max=255)])
    submit = SubmitField("Save Budget")

class EditBudgetForm(BudgetForm):
    # We can use the same fields for editing
    pass
