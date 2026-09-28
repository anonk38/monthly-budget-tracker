from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timezone
from decimal import Decimal
from app import db
from app.models.savings import Saving
from app.models.expense import Expense, Category

savings_bp = Blueprint('savings', __name__)

@savings_bp.route('/')
@login_required
def index():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))

    deposits = Saving.query.filter_by(user_id=current_user.id).order_by(Saving.date.desc(), Saving.id.desc()).all()
    total_deposited = sum((Decimal(str(d.amount)) for d in deposits), Decimal('0.00'))

    savings_cat = Category.query.filter_by(name='Savings').first()
    withdrawals = []
    total_withdrawn = Decimal('0.00')

    if savings_cat:
        withdrawals = Expense.query.filter_by(
            user_id=current_user.id, 
            category_id=savings_cat.id
        ).order_by(Expense.date.desc(), Expense.id.desc()).all()
        
        total_withdrawn = sum((Decimal(str(w.amount)) for w in withdrawals), Decimal('0.00'))

    net_savings = total_deposited - total_withdrawn

    return render_template(
        'savings/index.html',
        deposits=deposits,
        withdrawals=withdrawals,
        total_cumulative=net_savings,
        total_deposited=total_deposited,
        total_withdrawn=total_withdrawn
    )

@savings_bp.route('/add', methods=['POST'])
@login_required
def add():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))

    date_str = request.form.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    amount_str = request.form.get('amount')
    description = request.form.get('description', '').strip()
    redirect_target = request.form.get('redirect_target', 'dashboard')

    try:
        saving_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        amount = Decimal(amount_str)
        if not description:
            description = "Savings Deposit"

        new_saving = Saving(user_id=current_user.id, date=saving_date, amount=amount, description=description)
        db.session.add(new_saving)
        db.session.commit()
        flash(f'সেভিংসে ৳ {amount:,.2f} জমা করা হয়েছে!', 'success')
    except Exception:
        flash('সেভিংস জমা করতে সমস্যা হয়েছে।', 'danger')

    if redirect_target == 'savings':
        return redirect(url_for('savings.index'))
    return redirect(url_for('dashboard.index', month=saving_date.strftime('%Y-%m')))

@savings_bp.route('/reset-balance', methods=['POST'])
@login_required
def reset_balance():
    """ইউজার সরাসরি তার সেভিংস ব্যালেন্স ০ বা যেকোনো নির্দিষ্ট অংকে রিসেট করতে পারবেন"""
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))

    new_balance_str = request.form.get('target_balance', '0')
    redirect_target = request.form.get('redirect_target', 'dashboard')
    month_arg = request.form.get('month_year')

    try:
        new_balance = Decimal(new_balance_str)
        
        # বর্তমান সব ডিপোজিট ডিলিট করা
        Saving.query.filter_by(user_id=current_user.id).delete()
        
        # সেভিংস ক্যাটাগরি খরচ হিসাব করা
        savings_cat = Category.query.filter_by(name='Savings').first()
        total_withdrawn = Decimal('0.00')
        if savings_cat:
            w_recs = Expense.query.filter_by(user_id=current_user.id, category_id=savings_cat.id).all()
            total_withdrawn = sum((Decimal(str(w.amount)) for w in w_recs), Decimal('0.00'))

        # নেট ব্যালেন্স যেন ঠিক new_balance হয়
        adjusted_deposit = new_balance + total_withdrawn
        if adjusted_deposit > 0:
            reset_entry = Saving(
                user_id=current_user.id,
                date=datetime.now(timezone.utc).date(),
                amount=adjusted_deposit,
                description="Manual Balance Correction / Starting Balance"
            )
            db.session.add(reset_entry)

        db.session.commit()
        flash(f'সেভিংস ব্যালেন্স সফলভাবে ৳ {new_balance:,.2f} সেট করা হয়েছে!', 'success')
    except Exception:
        flash('ব্যালেন্স রিসেট করতে সমস্যা হয়েছে।', 'danger')

    if redirect_target == 'savings':
        return redirect(url_for('savings.index'))
    return redirect(url_for('dashboard.index', month=month_arg))

@savings_bp.route('/delete/<int:saving_id>', methods=['POST'])
@login_required
def delete(saving_id):
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))

    rec = Saving.query.filter_by(id=saving_id, user_id=current_user.id).first_or_404()
    db.session.delete(rec)
    db.session.commit()
    flash('সেভিংস রেকর্ড মুছে ফেলা হয়েছে!', 'info')
    return redirect(url_for('savings.index'))