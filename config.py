import os
from pathlib import Path
from dotenv import load_dotenv

# প্রজেক্ট রুট ডিরেক্টরি পাথ
BASE_DIR = Path(__file__).resolve().parent

# .env ফাইল লোড করা (যদি থাকে)
load_dotenv(BASE_DIR / '.env')

class Config:
    """বেস কনফিগারেশন"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-key-replace-in-production-anon')
    
    # ডেটাবেস পাথ: instance ফোল্ডারে SQLite ফাইল রাখা সর্বোত্তম প্র্যাকটিস
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f"sqlite:///{BASE_DIR / 'instance' / 'monthly_budget.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # কুকি ও সেশন সিকিউরিটি
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    
    # ফাইন্যান্সিয়াল ডিফল্ট সেটিংস
    DEFAULT_CURRENCY = os.environ.get('DEFAULT_CURRENCY', 'BDT')
    DEFAULT_MONTHLY_BUDGET = float(os.environ.get('DEFAULT_MONTHLY_BUDGET', 15000.00))

class DevelopmentConfig(Config):
    """ডেভেলপমেন্ট মোড"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """PythonAnywhere প্রোডাকশন মোড"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # HTTPS আবশ্যক

class TestingConfig(Config):
    """টেস্টিং মোড (ইন-মেমোরি ডেটাবেস)"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False

# মোড ম্যাপিং
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}