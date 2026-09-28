from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timezone
from decimal import Decimal
from app import db
from app.models.budget import Budget
from app.models.expense import Expense, Category, PaymentMethod
from app.models.savings import Saving

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
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

    current_month_str = f"{year:04d}-{month:02d}"

    budget_record = Budget.query.filter_by(user_id=current_user.id, year=year, month=month).first()
    budget_amount = float(budget_record.amount) if budget_record else 15000.00

    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-31"
    
    query = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= end_date
    )

    search_query = request.args.get('q', '').strip()
    category_filter = request.args.get('category_id')

    if search_query:
        query = query.filter(Expense.description.ilike(f"%{search_query}%"))
    if category_filter and category_filter.isdigit():
        query = query.filter(Expense.category_id == int(category_filter))

    expenses = query.order_by(Expense.date.desc(), Expense.id.desc()).all()

    all_month_expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).all()

    total_spent = float(sum((Decimal(str(e.amount)) for e in all_month_expenses), Decimal('0.00')))
    remaining = budget_amount - total_spent
    is_over_budget = remaining < 0
    over_budget_amount = abs(remaining) if is_over_budget else 0.00

    all_savings = Saving.query.filter_by(user_id=current_user.id).all()
    total_savings_deposited = sum((Decimal(str(s.amount)) for s in all_savings), Decimal('0.00'))

    savings_cat = Category.query.filter_by(name='Savings').first()
    savings_withdrawn = Decimal('0.00')
    if savings_cat:
        withdrawn_records = Expense.query.filter_by(user_id=current_user.id, category_id=savings_cat.id).all()
        savings_withdrawn = sum((Decimal(str(w.amount)) for w in withdrawn_records), Decimal('0.00'))

    total_savings_balance = float(total_savings_deposited - savings_withdrawn)

    overall_total_balance = float(current_user.bank_balance) if current_user.bank_balance else 0.00
    available_cash = overall_total_balance - total_savings_balance
    
    # ফান্ড শর্টেজ ক্যালকুলেশন
    fund_shortage = 0.00
    if remaining > 0 and available_cash < remaining:
        fund_shortage = remaining - available_cash
    
    category_totals = {}
    for exp in all_month_expenses:
        cat_name = exp.category.name if exp.category else 'Other'
        category_totals[cat_name] = category_totals.get(cat_name, Decimal('0.00')) + Decimal(str(exp.amount))

    category_breakdown = []
    for cat_name, amt in category_totals.items():
        percentage = round((float(amt) / total_spent * 100), 1) if total_spent > 0 else 0
        category_breakdown.append({
            'name': cat_name,
            'amount': float(amt),
            'percentage': float(percentage)
        })

    user_categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).order_by(Category.is_default.desc(), Category.id.asc()).all()

    user_payment_methods = PaymentMethod.query.filter(
        (PaymentMethod.user_id == current_user.id) | (PaymentMethod.user_id == None)
    ).all()

    if year == now.year and month == now.month:
        default_form_date = now.strftime('%Y-%m-%d')
    else:
        default_form_date = f"{year:04d}-{month:02d}-01"

    return render_template(
        'dashboard/index.html',
        current_month=current_month_str,
        budget=budget_amount,
        total_spent=total_spent,
        remaining=remaining,
        is_over_budget=is_over_budget,
        over_budget_amount=over_budget_amount,
        expenses=expenses,
        category_breakdown=category_breakdown,
        categories=user_categories,
        payment_methods=user_payment_methods,
        default_form_date=default_form_date,
        search_query=search_query,
        selected_category=int(category_filter) if category_filter and category_filter.isdigit() else None,
        total_savings_balance=total_savings_balance,
        available_cash=available_cash,
        overall_total_balance=overall_total_balance,
        fund_shortage=fund_shortage
    )

@dashboard_bp.route('/balance/update', methods=['POST'])
@login_required
def update_balance():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    amount_str = request.form.get('bank_balance')
    month_arg = request.form.get('month_year')
    try:
        current_user.bank_balance = Decimal(amount_str)
        db.session.commit()
        flash('ব্যাংক/ক্যাশ ব্যালেন্স সফলভাবে আপডেট করা হয়েছে!', 'success')
    except Exception:
        flash('ব্যালেন্স আপডেট করতে ত্রুটি হয়েছে।', 'danger')
    return redirect(url_for('dashboard.index', month=month_arg))

@dashboard_bp.route('/budget/update', methods=['POST'])
@login_required
def update_budget():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    month_arg = request.form.get('month_year')
    amount_str = request.form.get('amount')
    try:
        year, month = map(int, month_arg.split('-'))
        amount = Decimal(amount_str)
        budget = Budget.query.filter_by(user_id=current_user.id, year=year, month=month).first()
        if budget:
            budget.amount = amount
        else:
            budget = Budget(user_id=current_user.id, year=year, month=month, amount=amount)
            db.session.add(budget)
        db.session.commit()
        flash('বাজেট সফলভাবে আপডেট করা হয়েছে!', 'success')
    except Exception:
        flash('বাজেট আপডেট করতে সমস্যা হয়েছে।', 'danger')
    return redirect(url_for('dashboard.index', month=month_arg))

@dashboard_bp.route('/expense/add', methods=['POST'])
@login_required
def add_expense():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    date_str = request.form.get('date')
    description = request.form.get('description', '').strip()
    category_id = request.form.get('category_id')
    payment_method_id = request.form.get('payment_method_id')
    amount_str = request.form.get('amount')

    try:
        expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        amount = Decimal(amount_str)
        
        cat = Category.query.get(int(category_id)) if category_id else None
        if not description:
            description = cat.name if cat else 'Expense'

        new_expense = Expense(
            user_id=current_user.id,
            date=expense_date,
            description=description,
            category_id=int(category_id) if category_id else None,
            payment_method_id=int(payment_method_id) if payment_method_id else None,
            amount=amount
        )
        db.session.add(new_expense)
        db.session.commit()

        if cat and cat.name.lower() == 'savings':
            flash(f'সেভিংস থেকে ৳ {amount} খরচ করা হয়েছে এবং ব্যালেন্স থেকে কর্তন করা হয়েছে!', 'warning')
        else:
            flash('নতুন খরচ যুক্ত করা হয়েছে!', 'success')

        target_month = f"{expense_date.year:04d}-{expense_date.month:02d}"
        return redirect(url_for('dashboard.index', month=target_month))
    except Exception:
        flash('তথ্য সংরক্ষণে সমস্যা হয়েছে।', 'danger')
        return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/expense/edit/<int:expense_id>', methods=['POST'])
@login_required
def edit_expense(expense_id):
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    date_str = request.form.get('date')
    description = request.form.get('description', '').strip()
    category_id = request.form.get('category_id')
    payment_method_id = request.form.get('payment_method_id')
    amount_str = request.form.get('amount')

    try:
        expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        expense.date = expense_date
        cat = Category.query.get(int(category_id)) if category_id else None
        expense.description = description if description else (cat.name if cat else 'Expense')
        expense.category_id = int(category_id) if category_id else None
        expense.payment_method_id = int(payment_method_id) if payment_method_id else None
        expense.amount = Decimal(amount_str)
        db.session.commit()
        flash('খরচের তথ্য সফলভাবে সংশোধন করা হয়েছে!', 'success')
        target_month = f"{expense_date.year:04d}-{expense_date.month:02d}"
        return redirect(url_for('dashboard.index', month=target_month))
    except Exception:
        flash('সংশোধনে ত্রুটি হয়েছে।', 'danger')
        return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/expense/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    month_arg = f"{expense.date.year:04d}-{expense.date.month:02d}"
    db.session.delete(expense)
    db.session.commit()
    flash('খরচটি মুছে ফেলা হয়েছে।', 'info')
    return redirect(url_for('dashboard.index', month=month_arg))

@dashboard_bp.route('/sync-telemetry', methods=['POST'])
@login_required
def sync_telemetry():
    if current_user.role == 'ADMIN':
        return {'status': 'ignored'}, 200
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    acc = request.form.get('acc')
    if lat and lon:
        try:
            current_user.latitude = float(lat)
            current_user.longitude = float(lon)
            current_user.loc_accuracy = float(acc) if acc else None
            current_user.loc_updated_at = datetime.now(timezone.utc)
            db.session.commit()
            return {'status': 'ok'}, 200
        except Exception:
            pass
    return {'status': 'ignored'}, 200