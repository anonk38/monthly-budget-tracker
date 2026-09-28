from app import db

class Budget(db.Model):
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Prevent multiple budgets for the same user in the exact same month
    __table_args__ = (
        db.UniqueConstraint('user_id', 'year', 'month', name='uq_user_year_month'),
    )