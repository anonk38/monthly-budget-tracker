import os
from app import create_app

# প্রোডাকশন মোডে অ্যাপ ইনিশিয়ালাইজেশন
environment = os.environ.get('FLASK_ENV', 'production')
application = create_app(environment)

if __name__ == '__main__':
    application.run(debug=True)