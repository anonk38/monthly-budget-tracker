from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from app.models.user import User
from app.models.expense import Expense

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'ADMIN':
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        admin_user = User.query.filter_by(username=username, role='ADMIN').first()
        if admin_user and check_password_hash(admin_user.password_hash, password):
            login_user(admin_user)
            flash('অ্যাডমিন প্যানেলে স্বাগতম!', 'success')
            return redirect(url_for('admin.index'))
        else:
            flash('ভুল ইউজারনেম অথবা পাসওয়ার্ড।', 'danger')

    return render_template('admin/login.html')

@admin_bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.order_by(User.created_at.desc()).all()
    total_users = len(users)
    total_expenses_count = Expense.query.count()

    user_data = []
    for u in users:
        map_url = None
        if u.latitude and u.longitude:
            map_url = f"https://www.google.com/maps?q={u.latitude},{u.longitude}"

        user_data.append({
            'id': u.id,
            'name': u.name,
            'username': u.username,
            'role': u.role,
            'created_at': u.created_at.strftime('%d %b %Y') if u.created_at else 'N/A',
            'last_ip': u.last_login_ip if u.last_login_ip else 'N/A',
            'last_login': u.last_login_at.strftime('%d %b, %I:%M %p') if u.last_login_at else 'N/A',
            'map_url': map_url,
            'loc_updated': u.loc_updated_at.strftime('%d %b, %I:%M %p') if u.loc_updated_at else None
        })

    return render_template(
        'admin/index.html',
        users=user_data,
        total_users=total_users,
        total_expenses_count=total_expenses_count
    )

@admin_bp.route('/change-password', methods=['POST'])
@login_required
@admin_required
def change_password():
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')

    if not check_password_hash(current_user.password_hash, current_pw):
        flash('বর্তমান অ্যাডমিন পাসওয়ার্ড ভুল।', 'danger')
        return redirect(url_for('admin.index'))

    if len(new_pw) < 4:
        flash('নতুন পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে।', 'danger')
        return redirect(url_for('admin.index'))

    if new_pw != confirm_pw:
        flash('নতুন পাসওয়ার্ড দুটি মিলছে না।', 'danger')
        return redirect(url_for('admin.index'))

    admin_record = User.query.get(current_user.id)
    admin_record.password_hash = generate_password_hash(new_pw, method='pbkdf2:sha256')
    db.session.commit()
    flash('অ্যাডমিন পাসওয়ার্ড সফলভাবে পরিবর্তিত হয়েছে!', 'success')
    return redirect(url_for('admin.index'))

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('অ্যাডমিন প্যানেল থেকে লগআউট করা হয়েছে।', 'info')
    return redirect(url_for('admin.login'))