from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from app.models import User
from app.models.budget import Budget
from app.models.debt import Debt
from app.models.savings import Savings
from app.models.transaction import Transaction
from app.utils.email_service import send_email
from app import db

notifications_bp = Blueprint("notifications", __name__, url_prefix="/cron")


@notifications_bp.route("/notifications", methods=["GET"])
def run_notifications():
    today = datetime.utcnow().date()
    seven_days = today + timedelta(days=7)

    users = User.query.all()
    results = []

    for user in users:
        if not user.notify_email:
            continue  # skip if user disabled email notifications

        notices = []

        # ---------------------------
        # 1. Budget Limit Alerts
        # ---------------------------
        budgets = Budget.query.filter_by(user_id=user.id).all()

        for b in budgets:
            if b.spent >= (0.80 * b.amount) and b.spent < b.amount:
                notices.append(f"Budget '{b.name}' is now at 80% usage.")

            if b.spent >= b.amount:
                notices.append(f"Budget '{b.name}' has reached 100% usage.")

        # ---------------------------
        # 2. Debt/Credit Due Reminders
        # ---------------------------
        debts = Debt.query.filter_by(user_id=user.id).all()
        for d in debts:
            if d.due_date.date() == seven_days:
                notices.append(
                    f"Debt/Credit '{d.name}' is due in 7 days. Minimum payment: ₱{d.minimum_payment}"
                )

        # ---------------------------
        # 3. Savings Goal Reminder
        # ---------------------------
        savings = Savings.query.filter_by(user_id=user.id).all()

        for s in savings:
            if s.current_amount < (0.20 * s.target_amount):
                notices.append(f"Your savings goal '{s.goal_name}' is progressing slowly.")

        # Send all notices via email
        if notices:
            send_email(
                to=user.email,
                subject="Your Finance Notifications",
                body="\n".join(notices)
            )

        results.append({
            "user": user.email,
            "sent": len(notices),
            "messages": notices
        })

    return jsonify({"status": "completed", "data": results})
