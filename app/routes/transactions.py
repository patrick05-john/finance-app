from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from collections import defaultdict
from datetime import datetime, date
from app import db
from app.models.transaction import Transaction
from app.models.user import User
from app.models.budget import Budget
from app.models.savings import Savings
from app.models.debt import Debt
from app.models.plan import Plan
from app.forms.transaction import TransactionForm, EditTransactionForm

transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")

def get_active_budgets(user_id):
    today = date.today()
    budgets = Budget.query.filter(
        Budget.user_id == user_id,
        Budget.start_date <= today,
        Budget.end_date >= today
    ).all()

    for b in budgets:
        # Calculate total expenses tied to this budget
        expenses = Transaction.query.filter_by(budget_id=b.id, type="Expense").all()
        spent = sum(t.amount for t in expenses)

        # Dynamically attach the balance to the budget object
        b.balance = round(b.amount - spent, 2)

    return budgets

def reverse_transaction_logic(txn):
    user = User.query.get(txn.user_id)
    amount = txn.amount

    if txn.type == "Income":
        user.total_balance -= amount
    elif txn.type == "Expense":
        if txn.deduct_from == "income":
            user.total_balance += amount
        elif txn.deduct_from == "savings":
            savings = Savings.query.filter_by(user_id=txn.user_id).first()
            if savings:
                savings.current_amount += amount
        elif txn.deduct_from == "budget":
            pass
        elif txn.deduct_from == "debt":
            debt = Debt.query.filter_by(user_id=txn.user_id).first()
            if debt:
                debt.balance += amount
    elif txn.type in ["Debt Payment", "Credit Payment"]:
        debt = Debt.query.filter_by(user_id=txn.user_id).first()
        if debt:
            debt.balance += amount
        user.total_balance += amount

    db.session.commit()

def apply_transaction_logic(txn, deduct_from=None, budget_id=None):
    user = User.query.get(txn.user_id)
    amount = txn.amount

    if deduct_from:
        txn.deduct_from = deduct_from

    if txn.type == "Income":
        user.total_balance += amount
    elif txn.type == "Expense":
        if txn.deduct_from == "income":
            user.total_balance -= amount
        elif txn.deduct_from == "savings":
            savings = Savings.query.filter_by(user_id=txn.user_id).first()
            if savings:
                savings.current_amount -= amount
        elif txn.deduct_from == "budget":
            if budget_id:
                txn.budget_id = int(budget_id)
            else:
                active_budgets = get_active_budgets(txn.user_id)
                if active_budgets:
                    txn.budget_id = active_budgets[0].id
        elif txn.deduct_from == "debt":
            debt = Debt.query.filter_by(user_id=txn.user_id).first()
            if debt:
                debt.balance -= amount
    elif txn.type in ["Debt Payment", "Credit Payment"]:
        debt = Debt.query.filter_by(user_id=txn.user_id).first()
        if debt:
            debt.balance -= amount
        user.total_balance -= amount

    db.session.commit()

@transactions_bp.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    list_data = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()

    # Pass empty form and active budgets for the Add Transaction modal
    form = TransactionForm()
    active_budgets = get_active_budgets(user_id)

    return render_template("transactions/index.html", transactions=list_data, form=form, active_budgets=active_budgets)

@transactions_bp.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    user = User.query.get(user_id)

    if request.method == "POST":
        t_type = request.form.get("type")
        amount = float(request.form.get("amount", 0))
        category = request.form.get("category")
        description = request.form.get("description")
        date_str = request.form.get("date")
        date_value = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        deduct_from = request.form.get("deduct_from")
        budget_id = request.form.get("budget_id")

        if t_type == "Expense" and deduct_from == "income" and user.total_balance < amount:
            flash("Insufficient balance in main account!", "danger")
            return redirect(url_for("transactions.index"))

        new_transaction = Transaction(
            user_id=user_id, type=t_type, amount=amount,
            category=category, description=description, date=date_value,
        )

        try:
            db.session.add(new_transaction)
            apply_transaction_logic(new_transaction, deduct_from=deduct_from, budget_id=budget_id)
            db.session.commit()
            flash("Transaction added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while saving the transaction.", "danger")

        return redirect(url_for("transactions.index"))

    # Fallback redirect if accessed directly
    return redirect(url_for("transactions.index"))

@transactions_bp.route("/edit/<int:transaction_id>", methods=["GET", "POST"])
def edit(transaction_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    txn = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first_or_404()
    form = EditTransactionForm(obj=txn)

    if form.validate_on_submit():
        reverse_transaction_logic(txn)

        txn.type = form.type.data
        txn.amount = form.amount.data
        txn.category = form.category.data
        txn.description = form.description.data
        txn.date = form.date.data
        txn.deduct_from = form.deduct_from.data

        apply_transaction_logic(txn)
        db.session.commit()
        flash("Transaction updated successfully!", "success")
        return redirect(url_for("transactions.index"))

    return render_template("transactions/edit.html", form=form, txn=txn)

@transactions_bp.route("/delete/<int:transaction_id>", methods=['POST'])
def delete(transaction_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    txn = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first_or_404()

    reverse_transaction_logic(txn)
    db.session.delete(txn)
    db.session.commit()

    flash("Transaction deleted successfully!", "success")
    return redirect(url_for("transactions.index"))

@transactions_bp.route("/events")
def events():
    if "user_id" not in session:
        return jsonify([])

    user_id = session["user_id"]
    events_list = []

    # Add transactions to calendar
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    for t in transactions:
        color = "#10B981" if t.type == "Income" else "#EF4444"
        if "Payment" in t.type:
            color = "#F59E0B"

        # Format amount with 2 decimal places
        formatted_amount = f"{t.amount:,.2f}"
        
        events_list.append({
            "title": f"?{formatted_amount} - {t.category}",
            "start": t.date.strftime("%Y-%m-%d"),
            "color": color,
            "extendedProps": {"type": t.type, "category": t.category}
        })

    # Add plans to calendar
    plans = Plan.query.filter_by(user_id=user_id).all()
    for p in plans:
        plan_type_label = getattr(p, 'plan_type', 'Plan')
        formatted_amount = f"{p.amount:,.2f}"
        
        events_list.append({
            "title": f"[Plan] ?{formatted_amount} - {p.title}",
            "start": p.date.strftime("%Y-%m-%d"),
            "color": "#3B82F6" if "Income" in plan_type_label else "#F43F5E",
            "className": "planned-event",
            "extendedProps": {"type": plan_type_label, "category": "Forecast"}
        })

    # Add debts to calendar
    debts = Debt.query.filter_by(user_id=user_id).all()
    for d in debts:
        if hasattr(d, 'due_date') and d.due_date:
            formatted_amount = f"{d.minimum_payment:,.2f}" if hasattr(d, 'minimum_payment') else "0.00"
            events_list.append({
                "title": f"Due: {d.name} (?{formatted_amount})",
                "start": d.due_date.strftime("%Y-%m-%d"),
                "color": "#F59E0B",
                "extendedProps": {"type": "Debt Payment", "category": "Liability"}
            })

    return jsonify(events_list)

@transactions_bp.route("/add_plan", methods=["POST"])
def add_plan():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    title = request.form.get("title")
    plan_type = request.form.get("plan_type")
    amount = request.form.get("amount")
    date_str = request.form.get("date")

    if title and amount and date_str:
        try:
            plan_data = {
                "user_id": user_id,
                "title": title,
                "amount": float(amount),
                "date": datetime.strptime(date_str, "%Y-%m-%d").date()
            }
            if hasattr(Plan, 'plan_type'):
                plan_data["plan_type"] = plan_type

            new_plan = Plan(**plan_data)
            db.session.add(new_plan)
            db.session.commit()
            flash("Plan scheduled successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while saving your plan.", "danger")

    return redirect(url_for("transactions.index"))

