from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.user import User
from app.models.expense import Category, Expense

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
@login_required
def index():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))

    # ডিফল্ট (None) এবং ব্যবহারকারীর নিজস্ব ক্যাটাগরিগুলো দেখাবে
    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).order_by(Category.is_default.desc(), Category.id.asc()).all()
    return render_template('settings/index.html', categories=categories)

@settings_bp.route('/category/add', methods=['POST'])
@login_required
def add_category():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    name = request.form.get('name', '').strip()
    if not name:
        flash('ক্যাটাগরির নাম দিন।', 'danger')
        return redirect(url_for('settings.index'))

    new_cat = Category(name=name, user_id=current_user.id, is_default=False)
    db.session.add(new_cat)
    db.session.commit()
    flash('নতুন ক্যাটাগরি যুক্ত করা হয়েছে!', 'success')
    return redirect(url_for('settings.index'))

@settings_bp.route('/category/edit/<int:cat_id>', methods=['POST'])
@login_required
def edit_category(cat_id):
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    cat = Category.query.filter_by(id=cat_id, user_id=current_user.id).first_or_404()
    
    if cat.is_default:
        flash('ডিফল্ট ক্যাটাগরি পরিবর্তন করা সম্ভব নয়।', 'danger')
        return redirect(url_for('settings.index'))

    name = request.form.get('name', '').strip()
    if not name:
        flash('ক্যাটাগরির নাম দিন।', 'danger')
        return redirect(url_for('settings.index'))
    cat.name = name
    db.session.commit()
    flash('ক্যাটাগরি আপডেট করা হয়েছে!', 'success')
    return redirect(url_for('settings.index'))

@settings_bp.route('/category/delete/<int:cat_id>', methods=['POST'])
@login_required
def delete_category(cat_id):
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    
    cat = Category.query.filter_by(id=cat_id, user_id=current_user.id).first_or_404()
    
    if cat.is_default:
        flash('ডিফল্ট ক্যাটাগরি মুছে ফেলা সম্ভব নয়।', 'danger')
        return redirect(url_for('settings.index'))

    default_cat = Category.query.filter_by(name='Others', is_default=True).first()
    
    if default_cat:
        Expense.query.filter_by(category_id=cat.id, user_id=current_user.id).update({'category_id': default_cat.id})
    db.session.delete(cat)
    db.session.commit()
    flash('ক্যাটাগরি মুছে ফেলা হয়েছে!', 'info')
    return redirect(url_for('settings.index'))

@settings_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    name = request.form.get('name', '').strip()
    username = request.form.get('username', '').strip().lower()

    if not name or not username:
        flash('নাম ও ইউজারনেম আবশ্যক।', 'danger')
        return redirect(url_for('settings.index'))

    existing = User.query.filter(User.username == username, User.id != current_user.id).first()
    if existing:
        flash('এই ইউজারনেমটি অন্য কেউ ব্যবহার করছে।', 'danger')
        return redirect(url_for('settings.index'))

    user = User.query.get(current_user.id)
    user.name = name
    user.username = username
    db.session.commit()
    flash('প্রোফাইলের তথ্য আপডেট হয়েছে!', 'success')
    return redirect(url_for('settings.index'))

@settings_bp.route('/password/change', methods=['POST'])
@login_required
def change_password():
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin.index'))
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    user = User.query.get(current_user.id)
    if not check_password_hash(user.password_hash, current_password):
        flash('বর্তমান পাসওয়ার্ডটি সঠিক নয়।', 'danger')
        return redirect(url_for('settings.index'))

    if len(new_password) < 4:
        flash('পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে।', 'danger')
        return redirect(url_for('settings.index'))

    if new_password != confirm_password:
        flash('নতুন পাসওয়ার্ড দুটি মেলেনি।', 'danger')
        return redirect(url_for('settings.index'))

    user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()
    flash('পাসওয়ার্ড পরিবর্তন করা হয়েছে!', 'success')
    return redirect(url_for('settings.index'))