from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from app.models.user import User

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message='নাম দিন।'),
        Length(min=2, max=100, message='নাম কমপক্ষে ২ অক্ষরের হতে হবে।')
    ])
    username = StringField('Username', validators=[
        DataRequired(message='ইউজারনেম দিন।'),
        Length(min=3, max=30, message='ইউজারনেম ৩ থেকে ৩০ অক্ষরের হতে হবে।')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='পাসওয়ার্ড দিন।'),
        Length(min=4, message='পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে।')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='পাসওয়ার্ড নিশ্চিত করুন।'),
        EqualTo('password', message='পাসওয়ার্ড দুটি মেলেনি।')
    ])
    submit = SubmitField('অ্যাকাউন্ট তৈরি করুন')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data.strip().lower()).first()
        if user:
            raise ValidationError('এই ইউজারনেমটি ইতিমধ্যে ব্যবহৃত হয়েছে।')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='ইউজারনেম দিন।')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='পাসওয়ার্ড দিন।')
    ])
    remember = BooleanField('লগইন মনে রাখুন')
    submit = SubmitField('লগইন করুন')