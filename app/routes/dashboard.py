from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from datetime import datetime, date
from sqlalchemy import func
from .. import db
from ..models.user import User
from ..models.transaction import Transaction
from ..models.plan import Plan
from ..models.budget import Budget
import json
from collections import defaultdict
import calendar

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

def get_active_budgets(user_id):
    today = date.today()
    budgets = Budget.query.filter(
        Budget.user_id == user_id,
        Budget.start_date <= today,
        Budget.end_date >= today
    ).all()
    for budget in budgets:
        expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id, Transaction.type == "Expense", Transaction.budget_id == budget.id
        ).scalar() or 0.0
        budget.spent = expenses
        budget.remaining = budget.amount - budget.spent
        budget.balance = budget.remaining 
        budget.percent = min(100.0, (budget.spent / budget.amount) * 100) if budget.amount > 0 else 0.0
    return budgets

def apply_transaction_logic(txn, deduct_from=None, budget_id=None):
    user_id = txn.user_id
    user = User.query.get(user_id)
    amount = txn.amount
    if deduct_from: txn.deduct_from = deduct_from
    if txn.type == "Income":
        user.total_balance += amount
    elif txn.type == "Expense":
        if txn.deduct_from == "income": user.total_balance -= amount
        elif txn.deduct_from == "savings":
            from ..models.savings import Savings
            savings = Savings.query.filter_by(user_id=user_id).first()
            if savings: savings.current_amount -= amount
        elif txn.deduct_from == "budget" and budget_id:
            budget = Budget.query.get(budget_id)
            if budget and budget.user_id == user_id:
                txn.budget_id = int(budget_id)
        elif txn.deduct_from == "debt":
            from ..models.debt import Debt
            debt = Debt.query.filter_by(user_id=user_id).first()
            if debt: debt.balance -= amount
    elif txn.type in ["Debt Payment", "Credit Payment"]:
        from ..models.debt import Debt
        debt = Debt.query.filter_by(user_id=user_id).first()
        if debt: debt.balance -= amount
        user.total_balance -= amount
    db.session.commit()

@dashboard_bp.route("/")
def index():
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    user = User.query.get(user_id)

    current_month_start = datetime.now().replace(day=1).date()
    total_income_sum = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id, Transaction.type == "Income", Transaction.date >= current_month_start
    ).scalar() or 0.0
    total_expenses_sum = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id, Transaction.type == "Expense", Transaction.date >= current_month_start
    ).scalar() or 0.0
    total_balance = user.total_balance if user and user.total_balance else 0.0

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
        detail = {'label': t.category, 'amount': f"₱{amount:,.2f}", 'desc': t.description or 'No desc', 'is_plan': False, 'is_recurring': False}
        if t.type == 'Income':
            daily_aggs[date_str]['actual_inc']['total'] += amount
            daily_aggs[date_str]['actual_inc']['items'].append(detail)
        else:
            daily_aggs[date_str]['actual_exp']['total'] += amount
            daily_aggs[date_str]['actual_exp']['items'].append(detail)

    upcoming_reminders = []
    for plan in all_plans:
        amount = float(plan.amount)
        is_recurring = getattr(plan, 'is_recurring', False)
        recurring_day = getattr(plan, 'recurring_day', None)
        amount_rem_display = f"₱{plan.amount:,.2f}" if plan.amount > 0.1 else "Amount TBD"
        detail = {'label': plan.title, 'amount': amount_rem_display, 'desc': 'Scheduled plan', 'is_plan': True, 'is_recurring': is_recurring}

        if is_recurring and recurring_day:
            # 1. Forward-Project 12 months for Calendar
            for i in range(12):
                fm = today.month + i
                fy = today.year + (fm - 1) // 12
                fm = ((fm - 1) % 12) + 1
                max_days = calendar.monthrange(fy, fm)[1]
                actual_day = min(recurring_day, max_days)
                proj_date = date(fy, fm, actual_day)
                
                # Plot only if the projected date is on/after the creation month
                if proj_date >= plan.date.replace(day=1):
                    d_str = proj_date.strftime('%Y-%m-%d')
                    daily_aggs[d_str]['recurring']['total'] += amount
                    daily_aggs[d_str]['recurring']['items'].append(detail)

            # 2. Upcoming Reminders Logic (Find nearest future occurrence)
            max_days = calendar.monthrange(today.year, today.month)[1]
            actual_day = min(recurring_day, max_days)
            next_date = date(today.year, today.month, actual_day)
            
            if next_date < today:
                nm = today.month + 1
                ny = today.year
                if nm > 12:
                    nm = 1
                    ny += 1
                max_days = calendar.monthrange(ny, nm)[1]
                actual_day = min(recurring_day, max_days)
                next_date = date(ny, nm, actual_day)
            
            days_left = (next_date - today).days
            upcoming_reminders.append({
                "title": plan.title, "due_date": next_date.strftime("%b %d, %Y"), "amount": amount_rem_display, "days_left": days_left, 'is_recurring': True
            })

        else:
            # Standard Single Plan Processing
            date_str = plan.date.strftime('%Y-%m-%d')
            if plan.plan_type == 'Expected Income':
                daily_aggs[date_str]['planned_inc']['total'] += amount
                daily_aggs[date_str]['planned_inc']['items'].append(detail)
            else:
                daily_aggs[date_str]['planned_exp']['total'] += amount
                daily_aggs[date_str]['planned_exp']['items'].append(detail)

            if plan.date >= today:
                days_left = (plan.date - today).days
                upcoming_reminders.append({
                    "title": plan.title, "due_date": plan.date.strftime("%b %d, %Y"), "amount": amount_rem_display, "days_left": days_left, 'is_recurring': False
                })

    calendar_events = []
    for date_str, buckets in daily_aggs.items():
        pairs = [
            ('actual_inc', '₱ Income:', '#16A34A'),
            ('actual_exp', '₱ Expenses:', '#DC2626'),
            ('planned_inc', 'Planned Income:', '#3B82F6'),
            ('planned_exp', 'Planned Dues:', '#F59E0B'),
            ('recurring', '🔄 Recurring Dues:', '#8B5CF6')
        ]
        for bucket_key, title_prefix, color in pairs:
            data = buckets[bucket_key]
            if data['total'] > 0.1 or data['items']:
                calendar_events.append({
                    'title': f"{title_prefix} ₱{data['total']:,.2f}",
                    'start': date_str, 'color': color,
                    'extendedProps': {
                        'sourceType': bucket_key, 'PesoTotal': f"₱{data['total']:,.2f}",
                        'itemizedDetails': data['items']
                    }
                })

    upcoming_reminders = sorted(upcoming_reminders, key=lambda x: x['days_left'])[:5]
    recent_transactions = Transaction.query.filter(Transaction.user_id == user_id).order_by(Transaction.date.desc()).limit(5).all()
    active_budgets = get_active_budgets(user_id)

    return render_template(
        "dashboard/index.html", total_balance=f"{total_balance:,.2f}", total_income=f"{total_income_sum:,.2f}", total_expenses=f"{total_expenses_sum:,.2f}",
        recent_transactions=recent_transactions, upcoming_reminders=upcoming_reminders, calendar_events=json.dumps(calendar_events),
        active_budgets=active_budgets, today_date=today.strftime('%Y-%m-%d')
    )

@dashboard_bp.route("/add_transaction", methods=["POST"])
def add_transaction():
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    if request.method == "POST":
        t_type = request.form.get("type")
        amount = float(request.form.get("amount", 0))
        date_str = request.form.get("date")
        date_value = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        deduct_from = request.form.get("deduct_from")
        budget_id = request.form.get("budget_id")

        user = User.query.get(user_id)
        if t_type == "Expense" and deduct_from == "income" and user.total_balance < amount:
            flash("Insufficient balance in main account!", "danger")
            return redirect(url_for("dashboard.index"))

        new_transaction = Transaction(
            user_id=user_id, type=t_type, amount=amount, category=request.form.get("category"), description=request.form.get("description"), date=date_value,
        )
        try:
            db.session.add(new_transaction)
            apply_transaction_logic(new_transaction, deduct_from=deduct_from, budget_id=budget_id)
            db.session.commit()
            flash("Transaction added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while saving the transaction.", "danger")
    return redirect(url_for("dashboard.index"))

@dashboard_bp.route("/add_plan", methods=["POST"])
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
        
        plan_data = {
            "user_id": user_id, "title": final_title
        }
        if hasattr(Plan, 'plan_type'): plan_data["plan_type"] = model_plan_type
        plan_data["amount"] = float(amount_str) if amount_str else 0.0
        
        if hasattr(Plan, 'is_recurring'): plan_data["is_recurring"] = is_recurring
        if hasattr(Plan, 'recurring_day'):
            rec_day_str = request.form.get("recurring_day")
            if is_recurring and rec_day_str:
                rec_day = int(rec_day_str)
                plan_data["recurring_day"] = rec_day
                # Lock the base date strictly to the chosen recurring day
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
    return redirect(url_for("dashboard.index"))
