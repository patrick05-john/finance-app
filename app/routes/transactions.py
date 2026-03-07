from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from collections import defaultdict
from datetime import datetime, date
import calendar
import json
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
        expenses = Transaction.query.filter_by(budget_id=b.id, type="Expense").all()
        spent = sum(t.amount for t in expenses)
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
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    
    list_data = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()
    form = TransactionForm()
    active_budgets = get_active_budgets(user_id)

    # --- ADVANCED CALENDAR AGGREGATION LOGIC ---
    all_transactions = Transaction.query.filter_by(user_id=user_id).all()
    all_plans = Plan.query.filter_by(user_id=user_id).all()
    today = date.today()

    daily_aggs = defaultdict(lambda: {
        'actual_inc': {'total': 0.0, 'items': []},
        'actual_exp': {'total': 0.0, 'items': []},
        'planned_inc': {'total': 0.0, 'items': []},
        'planned_exp': {'total': 0.0, 'items': []},
        'recurring': {'total': 0.0, 'items': []}
    })

    for t in all_transactions:
        date_str = t.date.strftime('%Y-%m-%d')
        amount = float(t.amount)
        detail = {'label': t.category, 'amount': f"₱{amount:,.2f}", 'desc': t.description or 'No desc'}
        if t.type == 'Income':
            daily_aggs[date_str]['actual_inc']['total'] += amount
            daily_aggs[date_str]['actual_inc']['items'].append(detail)
        else:
            daily_aggs[date_str]['actual_exp']['total'] += amount
            daily_aggs[date_str]['actual_exp']['items'].append(detail)

    for plan in all_plans:
        amount = float(plan.amount)
        is_recurring = getattr(plan, 'is_recurring', False)
        recurring_day = getattr(plan, 'recurring_day', None)
        amount_rem_display = f"₱{plan.amount:,.2f}" if plan.amount > 0.1 else "Amount TBD"
        detail = {'label': plan.title, 'amount': amount_rem_display, 'desc': 'Scheduled plan'}

        if is_recurring and recurring_day:
            for i in range(12):
                fm = today.month + i
                fy = today.year + (fm - 1) // 12
                fm = ((fm - 1) % 12) + 1
                max_days = calendar.monthrange(fy, fm)[1]
                actual_day = min(recurring_day, max_days)
                proj_date = date(fy, fm, actual_day)
                
                if proj_date >= plan.date.replace(day=1):
                    d_str = proj_date.strftime('%Y-%m-%d')
                    daily_aggs[d_str]['recurring']['total'] += amount
                    daily_aggs[d_str]['recurring']['items'].append(detail)
        else:
            date_str = plan.date.strftime('%Y-%m-%d')
            if plan.plan_type == 'Expected Income':
                daily_aggs[date_str]['planned_inc']['total'] += amount
                daily_aggs[date_str]['planned_inc']['items'].append(detail)
            else:
                daily_aggs[date_str]['planned_exp']['total'] += amount
                daily_aggs[date_str]['planned_exp']['items'].append(detail)

    calendar_events = []
    for date_str, buckets in daily_aggs.items():
        pairs = [
            ('actual_inc', 'Income:', '#16A34A'),
            ('actual_exp', 'Expenses:', '#DC2626'),
            ('planned_inc', 'Planned Income:', '#3B82F6'),
            ('planned_exp', 'Planned Dues:', '#F59E0B'),
            ('recurring', 'Recurring Dues:', '#8B5CF6')
        ]
        for bucket_key, title_prefix, color in pairs:
            data = buckets[bucket_key]
            if data['total'] > 0.1 or data['items']:
                calendar_events.append({
                    'title': f"{title_prefix} ₱{data['total']:,.2f}",
                    'start': date_str, 'color': color,
                    'extendedProps': {
                        'sourceType': bucket_key, 'Total': f"₱{data['total']:,.2f}",
                        'itemizedDetails': data['items']
                    }
                })

    return render_template(
        "transactions/index.html", transactions=list_data, form=form, active_budgets=active_budgets,
        calendar_events=json.dumps(calendar_events), all_plans=all_plans, today_date=today.strftime('%Y-%m-%d')
    )

@transactions_bp.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session: return redirect(url_for("auth.login"))
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
            user_id=user_id, type=t_type, amount=amount, category=category, description=description, date=date_value,
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
    return redirect(url_for("transactions.index"))

@transactions_bp.route("/edit/<int:transaction_id>", methods=["GET", "POST"])
def edit(transaction_id):
    if "user_id" not in session: return redirect(url_for("auth.login"))
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
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    txn = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first_or_404()
    reverse_transaction_logic(txn)
    db.session.delete(txn)
    db.session.commit()
    flash("Transaction deleted successfully!", "success")
    return redirect(url_for("transactions.index"))

@transactions_bp.route("/add_plan", methods=["POST"])
def add_plan():
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    
    category = request.form.get("category")
    raw_title = request.form.get("title")
    amount_str = request.form.get("amount")
    
    is_recurring = False
    model_plan_type = "Expected Expense" 
    
    if category in ["Plan", "Transaction"]:
        model_plan_type = request.form.get("plan_type")
        is_recurring = request.form.get("is_recurring") == "yes"
    if category in ["Fixed Bills (Subscriptions)", "Electric Bills", "Water Bill"]:
        model_plan_type = "Expected Expense"
        is_recurring = True

    final_title = raw_title if category in ["Plan", "Transaction"] else f"{category}: {raw_title}"
    date_str = request.form.get("date")

    try:
        base_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        plan_data = { "user_id": user_id, "title": final_title }
        
        if hasattr(Plan, 'plan_type'): plan_data["plan_type"] = model_plan_type
        plan_data["amount"] = float(amount_str) if amount_str else 0.0
        
        if hasattr(Plan, 'is_recurring'): plan_data["is_recurring"] = is_recurring
        if hasattr(Plan, 'recurring_day'):
            rec_day_str = request.form.get("recurring_day")
            if is_recurring and rec_day_str:
                rec_day = int(rec_day_str)
                plan_data["recurring_day"] = rec_day
                max_days = calendar.monthrange(base_date.year, base_date.month)[1]
                actual_day = min(rec_day, max_days)
                base_date = date(base_date.year, base_date.month, actual_day)
            else:
                plan_data["recurring_day"] = None

        plan_data["date"] = base_date
        new_plan = Plan(**plan_data)
        db.session.add(new_plan)
        db.session.commit()
        flash("Plan scheduled successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while saving your plan.", "danger")
    return redirect(url_for("transactions.index"))

@transactions_bp.route("/delete_plan/<int:plan_id>", methods=["POST"])
def delete_plan(plan_id):
    if "user_id" not in session: return redirect(url_for("auth.login"))
    plan = Plan.query.get(plan_id)
    if plan and plan.user_id == session["user_id"]:
        db.session.delete(plan)
        db.session.commit()
        flash("Plan deleted successfully.", "success")
    return redirect(url_for("transactions.index"))

@transactions_bp.route("/edit_plan/<int:plan_id>", methods=["POST"])
def edit_plan(plan_id):
    if "user_id" not in session: return redirect(url_for("auth.login"))
    plan = Plan.query.get(plan_id)
    if not plan or plan.user_id != session["user_id"]:
        return redirect(url_for("transactions.index"))
    
    raw_title = request.form.get("title")
    amount_str = request.form.get("amount")
    is_recurring = request.form.get("is_recurring") == "yes"
    model_plan_type = request.form.get("plan_type", "Expected Expense")
    
    try:
        plan.title = raw_title
        if hasattr(plan, 'plan_type'): plan.plan_type = model_plan_type
        plan.amount = float(amount_str) if amount_str else 0.0
        
        date_str = request.form.get("date")
        base_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        
        if hasattr(plan, 'is_recurring'): plan.is_recurring = is_recurring
        if hasattr(plan, 'recurring_day'):
            rec_day_str = request.form.get("recurring_day")
            if is_recurring and rec_day_str:
                rec_day = int(rec_day_str)
                plan.recurring_day = rec_day
                max_days = calendar.monthrange(base_date.year, base_date.month)[1]
                actual_day = min(rec_day, max_days)
                base_date = date(base_date.year, base_date.month, actual_day)
            else:
                plan.recurring_day = None

        plan.date = base_date
        db.session.commit()
        flash("Plan updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the plan.", "danger")
    return redirect(url_for("transactions.index"))
