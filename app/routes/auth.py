from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timezone
from app import db
from app.models.user import User
from app.models.expense import Category, PaymentMethod
from app.forms import RegistrationForm, LoginForm

auth_bp = Blueprint('auth', __name__)

def seed_defaults_for_user(user_id):
    default_categories = [
        'Food & Groceries', 'Housing & Rent', 'Utilities & Bills',
        'Transportation', 'Healthcare & Medical', 'Shopping & Personal',
        'Entertainment & Dining', 'Education & Others'
    ]
    for cat_name in default_categories:
        db.session.add(Category(name=cat_name, user_id=user_id, is_default=True))
        
    default_payment_methods = ['Cash', 'Bank Transfer', 'Credit/Debit Card', 'bKash / Nagad / Rocket']
    for method_name in default_payment_methods:
        db.session.add(PaymentMethod(name=method_name, user_id=user_id, is_default=True))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(
            name=form.name.data.strip(),
            username=form.username.data.strip().lower(),
            email=None,
            password_hash=hashed_pw
        )
        db.session.add(new_user)
        db.session.flush()
        
        seed_defaults_for_user(new_user.id)
        db.session.commit()
        
        flash('আপনার অ্যাকাউন্ট সফলভাবে তৈরি হয়েছে! এখন লগইন করুন।', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        username_input = form.username.data.strip().lower()
        user = User.query.filter_by(username=username_input).first()
        
        if user and check_password_hash(user.password_hash, form.password.data):
            # ব্যবহারকারীর ক্লায়েন্ট আইপি সংগ্রহ
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if client_ip and ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()
            
            user.last_login_ip = client_ip
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()

            login_user(user, remember=form.remember.data)
            flash(f'স্বাগতম, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard.index'))
        else:
            flash('লগইন ব্যর্থ হয়েছে। ইউজারনেম অথবা পাসওয়ার্ড সঠিক নয়।', 'danger')
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('সফলভাবে লগআউট করা হয়েছে।', 'info')
    return redirect(url_for('auth.login'))