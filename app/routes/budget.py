from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from datetime import datetime, date, timedelta
from sqlalchemy import func
from app import db
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.user import User
from app.models.savings import Savings
from app.models.debt import Debt
from app.forms.budget_forms import BudgetForm, EditBudgetForm

budget_bp = Blueprint("budget", __name__, url_prefix="/budget")

def get_active_budgets(user_id):
    today = date.today()
    return Budget.query.filter(
        Budget.user_id == user_id,
        Budget.start_date <= today,
        Budget.end_date >= today
    ).all()

def calculate_budget_stats(budget, user_id):
    if not budget:
        return
    expenses_in_period = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "Expense",
        Transaction.budget_id == budget.id
    ).scalar() or 0.0

    budget.spent = expenses_in_period
    budget.remaining = budget.amount - budget.spent

    if budget.amount > 0:
        budget.percent = (budget.spent / budget.amount) * 100
    else:
        budget.percent = 0.0
    budget.percent = min(100.0, budget.percent)

@budget_bp.route("/")
def index():
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]

    # 1. BUDGET SECTION DATA
    active_budgets = get_active_budgets(user_id)
    total_active_amount = 0.0
    total_active_spent = 0.0
    total_active_remaining = 0.0

    for b in active_budgets:
        calculate_budget_stats(b, user_id)
        total_active_amount += b.amount
        total_active_spent += b.spent
        total_active_remaining += b.remaining

    previous_budgets = Budget.query.filter(
        Budget.user_id == user_id,
        Budget.end_date < date.today()
    ).order_by(Budget.end_date.desc()).all()

    for b in previous_budgets:
        calculate_budget_stats(b, user_id)

    # 2. EXPENSE SECTION DATA
    total_expenses = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id, Transaction.type == "Expense"
    ).scalar() or 0.0

    # BUG FIX: Use range logic to capture all times on the current day
    today = date.today()
    tomorrow = today + timedelta(days=1)
    today_expenses = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "Expense",
        Transaction.date >= today,
        Transaction.date < tomorrow
    ).scalar() or 0.0

    first_day_of_month = date.today().replace(day=1)
    monthly_expenses = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "Expense",
        Transaction.date >= first_day_of_month
    ).scalar() or 0.0

    expenses = Transaction.query.filter(
        Transaction.user_id == user_id, Transaction.type == "Expense"
    ).order_by(Transaction.date.desc()).limit(50).all()

    return render_template(
        "budget/index.html", active_budgets=active_budgets, total_active_amount=total_active_amount,
        total_active_spent=total_active_spent, total_active_remaining=total_active_remaining,
        previous_budgets=previous_budgets, total_expenses=total_expenses, today_expenses=today_expenses,
        monthly_expenses=monthly_expenses, expenses=expenses
    )

@budget_bp.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    form = BudgetForm()

    if form.validate_on_submit():
        name = form.name.data
        amount = form.amount.data
        funding_source = form.funding_source.data
        start_date = form.start_date.data
        end_date = form.end_date.data
        description = form.description.data
        user = User.query.get(user_id)

        try:
            if user.total_balance is None: user.total_balance = 0.0
            if funding_source == "income":
                if user.total_balance >= amount: user.total_balance -= amount
                else:
                    flash("Insufficient balance in main account!", "danger")
                    return redirect(url_for("budget.add"))
            elif funding_source == "savings":
                savings = Savings.query.filter_by(user_id=user_id).first()
                if not savings:
                    flash("No savings account found!", "danger")
                    return redirect(url_for("budget.add"))
                if savings.current_amount is None: savings.current_amount = 0.0
                if savings.current_amount >= amount: savings.current_amount -= amount
                else:
                    flash("Insufficient savings balance!", "danger")
                    return redirect(url_for("budget.add"))
            elif funding_source == "credit":
                debt = Debt.query.filter_by(user_id=user_id, debt_type="Credit Card").first()
                if debt:
                    if debt.balance is None: debt.balance = 0.0
                    debt.balance += amount
                else:
                    new_debt = Debt(
                        user_id=user_id, debt_type="Credit Card", name="Credit Card Budget",
                        balance=amount, limit_amount=amount * 2, due_date=date.today(), minimum_payment=0
                    )
                    db.session.add(new_debt)

            new_budget = Budget(user_id=user_id, name=name, amount=amount, funding_source=funding_source, start_date=start_date, end_date=end_date, description=description)
            db.session.add(new_budget)
            db.session.commit()
            flash("Budget created successfully!", "success")
            return redirect(url_for("budget.index"))
        except Exception as e:
            db.session.rollback()
            flash("An unexpected error occurred. Please try again.", "danger")
    return render_template("budget/add.html", form=form)

@budget_bp.route("/edit/<int:budget_id>", methods=["GET", "POST"])
def edit(budget_id):
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first_or_404()
    form = EditBudgetForm(obj=budget)

    if form.validate_on_submit():
        old_amount = budget.amount
        new_amount = form.amount.data
        old_source = budget.funding_source
        new_source = form.funding_source.data
        user = User.query.get(user_id)

        try:
            if user.total_balance is None: user.total_balance = 0.0
            if old_source == "income": user.total_balance += old_amount
            elif old_source == "savings":
                savings = Savings.query.filter_by(user_id=user_id).first()
                if savings:
                    if savings.current_amount is None: savings.current_amount = 0.0
                    savings.current_amount += old_amount
            elif old_source == "credit":
                debt = Debt.query.filter_by(user_id=user_id, debt_type="Credit Card").first()
                if debt:
                    if debt.balance is None: debt.balance = 0.0
                    debt.balance -= old_amount

            if new_source == "income":
                if user.total_balance >= new_amount: user.total_balance -= new_amount
                else:
                    flash("Insufficient balance!", "danger")
                    return redirect(url_for("budget.edit", budget_id=budget_id))
            elif new_source == "savings":
                savings = Savings.query.filter_by(user_id=user_id).first()
                if not savings:
                    flash("No savings account found!", "danger")
                    return redirect(url_for("budget.edit", budget_id=budget_id))
                if savings.current_amount >= new_amount: savings.current_amount -= new_amount
                else:
                    flash("Insufficient savings!", "danger")
                    return redirect(url_for("budget.edit", budget_id=budget_id))
            elif new_source == "credit":
                debt = Debt.query.filter_by(user_id=user_id, debt_type="Credit Card").first()
                if debt: debt.balance += new_amount
                else:
                    new_debt = Debt(
                        user_id=user_id, debt_type="Credit Card", name="Credit Card Budget",
                        balance=new_amount, limit_amount=new_amount * 2, due_date=date.today(), minimum_payment=0
                    )
                    db.session.add(new_debt)

            form.populate_obj(budget)
            db.session.commit()
            flash("Budget updated successfully!", "success")
            return redirect(url_for("budget.index"))
        except Exception as e:
            db.session.rollback()
            flash("Error updating budget.", "danger")
    return render_template("budget/edit.html", form=form, budget=budget)

@budget_bp.route("/delete/<int:budget_id>", methods=["POST"])
def delete(budget_id):
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first_or_404()
    expenses = Transaction.query.filter_by(budget_id=budget_id).all()
    if expenses:
        flash("Cannot delete a budget with linked expenses.", "danger")
        return redirect(url_for("budget.index"))
    user = User.query.get(user_id)
    if user.total_balance is None: user.total_balance = 0.0

    try:
        if budget.funding_source == "income": user.total_balance += budget.amount
        elif budget.funding_source == "savings":
            savings = Savings.query.filter_by(user_id=user_id).first()
            if savings: savings.current_amount += budget.amount
        elif budget.funding_source == "credit":
            debt = Debt.query.filter_by(user_id=user_id, debt_type="Credit Card").first()
            if debt: debt.balance -= budget.amount

        db.session.delete(budget)
        db.session.commit()
        flash("Budget deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting budget.", "danger")
    return redirect(url_for("budget.index"))
