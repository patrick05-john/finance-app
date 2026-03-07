from flask import Blueprint, render_template, session, redirect, url_for, send_file, request, jsonify
from app.models.transaction import Transaction
from app.models.plan import Plan
from app.models.user import User
from app.models.savings import Savings
from app.models.debt import Debt
from app import db
from datetime import datetime, timedelta, date
import calendar
import pandas as pd
import numpy as np
import io

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

@reports_bp.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    user_id = session["user_id"]
    user = User.query.get(user_id)
    savings = Savings.query.filter_by(user_id=user_id).all()
    debts = Debt.query.filter_by(user_id=user_id).all()

    total_balance = user.total_balance if user and user.total_balance else 0.0
    total_savings = sum(s.current_amount for s in savings if s.current_amount)
    total_debt = sum(d.balance for d in debts if d.balance)

    return render_template(
        "reports/index.html",
        total_balance=total_balance,
        total_savings=total_savings,
        total_debt=total_debt
    )

@reports_bp.route("/summary")
def summary():
    if "user_id" not in session:
        return jsonify({})
    
    user_id = session["user_id"]
    trx = Transaction.query.filter_by(user_id=user_id).all()
    
    if not trx:
        return jsonify({"status": "empty"})
        
    df = pd.DataFrame([{"date": t.date, "type": t.type, "amount": float(t.amount)} for t in trx])
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%b %Y")
    df["month_sort"] = df["date"].dt.to_period("M")

    grouped = df.groupby(["month_sort", "month", "type"])["amount"].sum().reset_index()
    months_sorted = df.sort_values("month_sort")["month"].unique().tolist()

    monthly_income = {}
    monthly_expense = {}

    for _, row in grouped.iterrows():
        if row["type"] == "Income":
            monthly_income[row["month"]] = row["amount"]
        elif row["type"] == "Expense":
            monthly_expense[row["month"]] = row["amount"]

    return jsonify({
        "months": months_sorted,
        "income": [monthly_income.get(m, 0.0) for m in months_sorted],
        "expense": [monthly_expense.get(m, 0.0) for m in months_sorted]
    })

@reports_bp.route("/categories")
def categories():
    if "user_id" not in session:
        return jsonify({})
        
    user_id = session["user_id"]
    trx = Transaction.query.filter_by(user_id=user_id).all()
    
    if not trx:
        return jsonify({"status": "empty"})
        
    df = pd.DataFrame([{"category": t.category, "amount": float(t.amount), "type": t.type} for t in trx])
    
    exp_df = df[df["type"] == "Expense"]
    inc_df = df[df["type"] == "Income"]

    expense_cat = {k: float(v) for k, v in exp_df.groupby("category")["amount"].sum().to_dict().items()} if not exp_df.empty else {}
    income_cat = {k: float(v) for k, v in inc_df.groupby("category")["amount"].sum().to_dict().items()} if not inc_df.empty else {}

    return jsonify({
        "expense": expense_cat,
        "income": income_cat
    })

@reports_bp.route("/forecast")
def forecast():
    if "user_id" not in session:
        return jsonify({"forecast": 0.0})

    user_id = session["user_id"]
    today = date.today()

    # Target next calendar month
    target_month = today.month + 1
    target_year = today.year
    if target_month > 12:
        target_month = 1
        target_year += 1

    all_plans = Plan.query.filter_by(user_id=user_id).all()
    fixed_forecast = 0.0

    for plan in all_plans:
        # Ignore Expected Income plans entirely
        p_type = getattr(plan, 'plan_type', '')
        if p_type in ['Expected Income', 'Income']:
            continue
            
        amount = float(plan.amount) if plan.amount else 0.0
        
        # Handle string booleans safely
        is_rec_raw = getattr(plan, 'is_recurring', False)
        is_rec = str(is_rec_raw).strip().lower() in ['true', '1', 'yes']
        rec_day = getattr(plan, 'recurring_day', None)

        if is_rec and rec_day:
            max_days = calendar.monthrange(target_year, target_month)[1]
            actual_day = min(int(rec_day), max_days)
            proj_date = date(target_year, target_month, actual_day)
            
            if proj_date >= plan.date.replace(day=1):
                fixed_forecast += amount
        else:
            if plan.date and plan.date.year == target_year and plan.date.month == target_month:
                fixed_forecast += amount

    essential_categories = [
        "Transport", "Transportation", 
        "Groceries", "Foods", 
        "Health & Wellness", "Health", 
        "Utilities", "Electric Bills", "Water Bill"
    ]
    
    thirty_days_ago = today - timedelta(days=30)

    past_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.type == "Expense",
        Transaction.date >= thirty_days_ago,
        Transaction.date <= today,
        Transaction.category.in_(essential_categories)
    ).all()

    monthly_variable_prediction = sum(float(t.amount) for t in past_transactions)

    total_forecast = fixed_forecast + monthly_variable_prediction

    return jsonify({
        "forecast": float(total_forecast),
        "breakdown": {
            "fixed_plans": float(fixed_forecast),
            "predicted_variable": float(monthly_variable_prediction)
        }
    })

@reports_bp.route("/export")
def export_csv():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    trx = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()

    export_data = []
    for t in trx:
        export_data.append({
            "Transaction Month": t.date.strftime("%B %Y"),
            "Exact Date": t.date.strftime("%b %d, %Y"),
            "Type": t.type,
            "Category": t.category,
            "Description / Product": t.description if t.description else "N/A",
            "Amount (PHP)": t.amount
        })

    df = pd.DataFrame(export_data)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    today_str = datetime.today().strftime('%Y-%m-%d')
    filename = f"financial_report_{today_str}.csv"

    return send_file(io.BytesIO(output.read().encode()), mimetype="text/csv", as_attachment=True, download_name=filename)