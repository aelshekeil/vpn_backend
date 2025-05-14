# /home/ubuntu/vpn_backend/src/models/user.py
from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # Increased length for stronger hashes
    is_vip = db.Column(db.Boolean, default=False, nullable=False)
    trial_expires_at = db.Column(db.DateTime, nullable=True)
    wg_config_path = db.Column(db.String(255), nullable=True) # Path to user's WireGuard config file
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    stripe_customer_id = db.Column(db.String(255), nullable=True)  # Added for Stripe integration
    stripe_subscription_id = db.Column(db.String(255), nullable=True) # Added for Stripe integration
    # Add more fields as needed, e.g., for bandwidth tracking, payment status, etc.

    def __repr__(self):
        return f"<User {self.email}>"
