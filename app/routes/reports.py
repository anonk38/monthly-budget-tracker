import csv
import io
from flask import Blueprint, render_template, request, Response, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timezone
from decimal import Decimal
from app.models.budget import Budget
from app.models.expense import Expense, Category
from app.models.savings import Saving

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))

    now = datetime.now(timezone.utc)
    month_arg = request.args.get('month')
    if month_arg:
        try:
            year, month = map(int, month_arg.split('-'))
        except ValueError:
            year, month = now.year, now.month
    else:
        year, month = now.year, now.month

    selected_month = f"{year:04d}-{month:02d}"

    budget_record = Budget.query.filter_by(user_id=current_user.id, year=year, month=month).first()
    budget_val = float(budget_record.amount) if budget_record else 15000.00

    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-31"
    
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).all()

    total_spent_val = float(sum((Decimal(str(e.amount)) for e in expenses), Decimal('0.00')))
    remaining_val = budget_val - total_spent_val
    total_tx_count = len(expenses)
    
    daily_avg_val = round(total_spent_val / 30.0, 2) if total_spent_val > 0 else 0.0
    largest_exp = max(expenses, key=lambda x: Decimal(str(x.amount))) if expenses else None
    largest_exp_amount = float(largest_exp.amount) if largest_exp else 0.0
    largest_exp_desc = largest_exp.description if largest_exp else '-'

    month_savings_records = Saving.query.filter(
        Saving.user_id == current_user.id,
        Saving.date >= start_date,
        Saving.date <= end_date
    ).all()
    month_saved_val = float(sum((Decimal(str(s.amount)) for s in month_savings_records), Decimal('0.00')))
    
    all_s = Saving.query.filter_by(user_id=current_user.id).all()
    total_deposited = sum((Decimal(str(s.amount)) for s in all_s), Decimal('0.00'))
    
    savings_cat = Category.query.filter_by(name='Savings').first()
    savings_withdrawn = Decimal('0.00')
    if savings_cat:
        withdrawn_records = Expense.query.filter_by(user_id=current_user.id, category_id=savings_cat.id).all()
        savings_withdrawn = sum((Decimal(str(w.amount)) for w in withdrawn_records), Decimal('0.00'))

    total_saved_lifetime_val = float(total_deposited - savings_withdrawn)

    return render_template(
        'reports/index.html',
        selected_month=selected_month,
        budget=f"{budget_val:,.2f}",
        total_spent=f"{total_spent_val:,.2f}",
        remaining=f"{abs(remaining_val):,.2f}",
        is_over_budget=(remaining_val < 0),
        daily_avg=f"{daily_avg_val:,.2f}",
        largest_expense_amount=f"{largest_exp_amount:,.2f}",
        largest_expense_desc=largest_exp_desc,
        total_transactions=total_tx_count,
        month_saved=f"{month_saved_val:,.2f}",
        total_saved_lifetime=f"{total_saved_lifetime_val:,.2f}"
    )

@reports_bp.route('/history')
@login_required
def history():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))

    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    history_dict = {}

    for exp in expenses:
        key = f"{exp.date.year:04d}-{exp.date.month:02d}"
        if key not in history_dict:
            b_rec = Budget.query.filter_by(user_id=current_user.id, year=exp.date.year, month=exp.date.month).first()
            b_amt = Decimal(str(b_rec.amount)) if b_rec else Decimal('15000.00')
            history_dict[key] = {
                'month_str': exp.date.strftime('%B %Y'),
                'budget': b_amt,
                'spent': Decimal('0.00')
            }
        history_dict[key]['spent'] += Decimal(str(exp.amount))

    history_list = list(history_dict.values())
    return render_template('reports/history.html', history_list=history_list)

@reports_bp.route('/export-csv')
@login_required
def export_csv():
    month_arg = request.args.get('month')
    now = datetime.now(timezone.utc)
    if month_arg:
        try:
            year, month = map(int, month_arg.split('-'))
        except ValueError:
            year, month = now.year, now.month
    else:
        year, month = now.year, now.month

    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-31"

    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).order_by(Expense.date.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Description', 'Category', 'Payment Method', 'Amount (BDT)'])

    for exp in expenses:
        writer.writerow([
            exp.date.strftime('%Y-%m-%d'),
            exp.description or '',
            exp.category.name if exp.category else 'Other',
            exp.payment_method.name if exp.payment_method else 'Cash',
            float(exp.amount)
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=monthly_expense_{year}_{month}.csv"}
    )
