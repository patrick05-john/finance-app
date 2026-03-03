from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from app.forms.debt_forms import DebtForm, PaymentForm
from app.models.user import User
from app.models.debt import Debt
from app.models.transaction import Transaction
from app.models.income import Income
from app import db
from datetime import datetime, date

debt_bp = Blueprint("debt", __name__, url_prefix="/debt")

@debt_bp.route("/")
def index():
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    debts = Debt.query.filter_by(user_id=user_id).all()
    user = User.query.get(user_id)
    return render_template("debt/index.html", debts=debts, user=user)

@debt_bp.route("/add", methods=["POST"])
def add():
    if "user_id" not in session: return redirect(url_for("auth.login"))
    
    # Get form data directly from request.form
    debt_type = request.form.get("debt_type")
    name = request.form.get("name")
    balance = float(request.form.get("balance", 0))
    minimum_payment = float(request.form.get("minimum_payment", 0))
    monthly_due_date = int(request.form.get("monthly_due_date", 1))
    limit_amount = float(request.form.get("limit_amount", 0)) if request.form.get("limit_amount") else None
    
    # Loan-specific fields
    loan_start_date = None
    loan_end_date = None
    if debt_type == "Loan":
        loan_start_date_str = request.form.get("loan_start_date")
        loan_end_date_str = request.form.get("loan_end_date")
        if loan_start_date_str:
            loan_start_date = datetime.strptime(loan_start_date_str, "%Y-%m-%d").date()
        if loan_end_date_str:
            loan_end_date = datetime.strptime(loan_end_date_str, "%Y-%m-%d").date()

    new_debt = Debt(
        user_id=session["user_id"],
        debt_type=debt_type,
        name=name,
        limit_amount=limit_amount if debt_type == "Credit Card" else None,
        balance=balance,
        minimum_payment=minimum_payment,
        due_date=date.today(),
        monthly_due_date=monthly_due_date,
        loan_start_date=loan_start_date if debt_type == "Loan" else None,
        loan_end_date=loan_end_date if debt_type == "Loan" else None
    )

    db.session.add(new_debt)
    db.session.commit()
    flash("Debt/Credit added successfully!", "success")
    return redirect(url_for("debt.index"))

@debt_bp.route("/<int:debt_id>/pay", methods=["POST"])
def pay(debt_id):
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    debt = Debt.query.get_or_404(debt_id)
    
    # Get current user for total balance
    user = User.query.get(user_id)
    
    payment = float(request.form.get("amount", 0))
    
    # Check if user has enough balance
    if user.total_balance < payment:
        flash("Insufficient balance in main account!", "danger")
        return redirect(url_for("debt.index"))
    
    # 1. Deduct from Debt Balance
    debt.balance -= payment
    if debt.balance < 0: debt.balance = 0

    # 2. Deduct from total balance
    user.total_balance -= payment

    # 3. Log the Transaction
    new_payment = Transaction(
        user_id=user_id,
        type="Expense",
        amount=payment,
        category="Debt Payment",
        description=f"Payment for {debt.name}",
        deduct_from="Main Balance"
    )

    db.session.add(new_payment)
    db.session.commit()
    flash("Payment added successfully!", "success")
    return redirect(url_for("debt.index"))

@debt_bp.route("/edit/<int:debt_id>", methods=["GET", "POST"])
def edit_debt(debt_id):
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    debt = Debt.query.filter_by(id=debt_id, user_id=user_id).first_or_404()

    if request.method == "POST":
        debt.name = request.form["name"]
        debt.debt_type = request.form["type"]
        debt.limit_amount = float(request.form["limit"]) if request.form.get("limit") and request.form["type"] == "Credit Card" else None
        debt.balance = float(request.form["balance"])
        debt.minimum_payment = float(request.form["minimum_payment"])

        due_day_str = request.form.get("monthly_due_date", "").strip()
        debt.monthly_due_date = int(due_day_str) if due_day_str and due_day_str.isdigit() else debt.monthly_due_date
        debt.due_date = debt.due_date or date.today()

        if request.form["type"] == "Loan":
            loan_start_date_str = request.form.get("loan_start_date", "").strip()
            debt.loan_start_date = datetime.strptime(loan_start_date_str, "%Y-%m-%d").date() if loan_start_date_str else None

            loan_end_date_str = request.form.get("loan_end_date", "").strip()
            debt.loan_end_date = datetime.strptime(loan_end_date_str, "%Y-%m-%d").date() if loan_end_date_str else None
        else:
            debt.loan_start_date = None
            debt.loan_end_date = None

        db.session.commit()
        flash("Debt / Credit account updated successfully!", "success")
        return redirect(url_for("debt.index"))

    # Return JSON for GET requests
    return jsonify({
        'id': debt.id,
        'name': debt.name,
        'debt_type': debt.debt_type,
        'balance': debt.balance,
        'minimum_payment': debt.minimum_payment,
        'monthly_due_date': debt.monthly_due_date,
        'limit_amount': debt.limit_amount,
        'loan_start_date': debt.loan_start_date.isoformat() if debt.loan_start_date else None,
        'loan_end_date': debt.loan_end_date.isoformat() if debt.loan_end_date else None
    })

@debt_bp.route("/delete/<int:debt_id>")
def delete_debt(debt_id):
    if "user_id" not in session: return redirect(url_for("auth.login"))
    user_id = session["user_id"]
    debt = Debt.query.filter_by(id=debt_id, user_id=user_id).first_or_404()

    db.session.delete(debt)
    db.session.commit()
    flash("Debt / Credit account deleted!", "success")
    return redirect(url_for("debt.index"))






