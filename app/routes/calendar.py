from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, flash, send_file
from app.models.transaction import Transaction
from app.models.savings import Savings
from app.models.debt import Debt
from app.models.budget import Budget
from app.models.plan import Plan
from datetime import datetime
import pandas as pd
import io
from app import db

calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")

@calendar_bp.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("calendar/index.html")

@calendar_bp.route("/add_plan", methods=["POST"])
def add_plan():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    title = request.form.get("title")
    amount = float(request.form.get("amount", 0))
    plan_type = request.form.get("plan_type")
    date_str = request.form.get("date")

    if title and date_str:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        new_plan = Plan(user_id=user_id, title=title, amount=amount, plan_type=plan_type, date=date_obj)
        db.session.add(new_plan)
        db.session.commit()
        flash("Upcoming plan added successfully.", "success")

    return redirect(url_for("calendar.index"))

@calendar_bp.route("/events")
def events():
    if "user_id" not in session:
        return jsonify([])

    user_id = session["user_id"]
    events = []

    # 1. TRANSACTIONS
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    for t in transactions:
        color = "#10B981" if t.type == "Income" else "#EF4444" # Updated to modern Tailwind-like colors
        if t.category == "Savings Deposit":
            color = "#3B82F6"
        events.append({
            "title": f"{t.type}: ₱{t.amount:,.2f}",
            "start": t.date.strftime("%Y-%m-%d"),
            "color": color,
            "extendedProps": {"category": t.category, "type": "Transaction"}
        })

    # 2. DEBTS
    debts = Debt.query.filter_by(user_id=user_id).all()
    for d in debts:
        events.append({
            "title": f"Due: {d.name} (₱{d.minimum_payment:,.2f})",
            "start": d.due_date.strftime("%Y-%m-%d"),
            "color": "#F59E0B",
            "extendedProps": {"category": "Liability", "type": "Debt"}
        })

    # 3. BUDGETS
    budgets = Budget.query.filter_by(user_id=user_id).all()
    for b in budgets:
        events.append({
            "title": f"Budget Start: {b.name}",
            "start": b.start_date.strftime("%Y-%m-%d"),
            "color": "#8B5CF6",
            "extendedProps": {"category": "Budgeting", "type": "Budget"}
        })
        events.append({
            "title": f"Budget End: {b.name}",
            "start": b.end_date.strftime("%Y-%m-%d"),
            "color": "#6D28D9",
            "extendedProps": {"category": "Budgeting", "type": "Budget"}
        })

    # 4. PLANNED EVENTS
    plans = Plan.query.filter_by(user_id=user_id).all()
    for p in plans:
        color = "#0EA5E9" if p.plan_type == "Income" else "#F43F5E"
        events.append({
            "title": f"[Plan] {p.title}: ₱{p.amount:,.2f}",
            "start": p.date.strftime("%Y-%m-%d"),
            "color": color,
            "className": "planned-event",
            "extendedProps": {"category": "Forecast", "type": f"Planned {p.plan_type}"}
        })

    return jsonify(events)

@calendar_bp.route("/export")
def export_csv():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    user_id = session["user_id"]
    export_data = []

    transactions = Transaction.query.filter_by(user_id=user_id).all()
    for t in transactions:
        export_data.append({"Date": t.date.strftime("%Y-%m-%d"), "Type": "Transaction", "Record": t.type, "Category": t.category, "Amount": t.amount})

    debts = Debt.query.filter_by(user_id=user_id).all()
    for d in debts:
        export_data.append({"Date": d.due_date.strftime("%Y-%m-%d"), "Type": "Debt", "Record": d.name, "Category": "Liability Due", "Amount": d.minimum_payment})

    plans = Plan.query.filter_by(user_id=user_id).all()
    for p in plans:
        export_data.append({"Date": p.date.strftime("%Y-%m-%d"), "Type": f"Planned {p.plan_type}", "Record": p.title, "Category": "Forecast", "Amount": p.amount})

    df = pd.DataFrame(export_data)
    if not df.empty:
        df = df.sort_values(by="Date", ascending=False)
    
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype="text/csv", as_attachment=True, download_name="calendar_schedule.csv")
