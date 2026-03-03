from flask import Blueprint, render_template, session, redirect, url_for, send_file, request
from app.models.transaction import Transaction
from app.models.plan import Plan
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
    return render_template("reports/index.html")

@reports_bp.route("/summary")
def summary():
    if "user_id" not in session:
        return {}
    user_id = session["user_id"]
    trx = Transaction.query.filter_by(user_id=user_id).all()
    if not trx:
        return {"status": "empty"}
    df = pd.DataFrame([{"date": t.date, "type": t.type, "amount": t.amount, "category": t.category} for t in trx])
    df["date"] = pd.to_datetime(df["date"])

    daily = df.groupby(df["date"].dt.date)["amount"].sum()
    daily = {str(k): float(v) for k, v in daily.to_dict().items()}

    weekly = df.groupby(df["date"].dt.isocalendar().week)["amount"].sum()
    weekly = {str(k): float(v) for k, v in weekly.to_dict().items()}

    monthly = df.groupby(df["date"].dt.to_period("M"))["amount"].sum()
    monthly = {str(k): float(v) for k, v in monthly.to_dict().items()}
    return {"daily": daily, "weekly": weekly, "monthly": monthly}

@reports_bp.route("/categories")
def categories():
    if "user_id" not in session:
        return {}
    user_id = session["user_id"]
    trx = Transaction.query.filter_by(user_id=user_id, type="Expense").all()
    df = pd.DataFrame([{"category": t.category, "amount": t.amount} for t in trx])
    if df.empty:
        return {"status": "empty"}
    category_total = df.groupby("category")["amount"].sum()
    category_total = {k: float(v) for k, v in category_total.to_dict().items()}
    return category_total

@reports_bp.route("/forecast")
def forecast():
    if "user_id" not in session:
        return {"forecast": 0.0}

    user_id = session["user_id"]
    today = date.today()

    # 1. FIXED PLANS: Calculate start and end dates of the NEXT calendar month
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)

    _, last_day = calendar.monthrange(next_month_start.year, next_month_start.month)
    next_month_end = date(next_month_start.year, next_month_start.month, last_day)

    # Sum up all scheduled plans for next month
    upcoming_plans = Plan.query.filter(
        Plan.user_id == user_id,
        Plan.date >= next_month_start,
        Plan.date <= next_month_end
    ).all()

    fixed_forecast = sum(plan.amount for plan in upcoming_plans)

    # 2. VARIABLE EXPENSES: Predictive 90-Day Rolling Average
    ninety_days_ago = today - timedelta(days=90)

    past_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.type == "Expense",
        Transaction.date >= ninety_days_ago,
        Transaction.date <= today
    ).all()

    # Sum the last 3 months of expenses and divide by 3 for a monthly average
    past_expenses_total = sum(t.amount for t in past_transactions)
    monthly_variable_prediction = past_expenses_total / 3.0

    # 3. Combine both for the final total forecast
    total_forecast = fixed_forecast + monthly_variable_prediction

    return {
        "forecast": float(total_forecast),
        "breakdown": {
            "fixed_plans": float(fixed_forecast),
            "predicted_variable": float(monthly_variable_prediction)
        }
    }

@reports_bp.route("/export")
def export_csv():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
        
    user_id = session["user_id"]
    
    # Get all transactions but order them by newest first
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