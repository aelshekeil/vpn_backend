# /home/ubuntu/vpn_backend/src/routes/auth.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import jwt # PyJWT

from src.models.user import db, User
from ..app import app # To access app.config for SECRET_KEY

# Placeholder for wg-easy interaction
# In a real scenario, you would import a library or use subprocess to call wg-easy CLI/API
def create_wireguard_user(email):
    # This is a placeholder. Replace with actual wg-easy interaction.
    # For example, call wg-easy API to create a user and get their config path.
    print(f"Simulating WireGuard user creation for: {email}")
    return f"/etc/wireguard/clients/{email.split("@")[0]}.conf" # Example path

def get_wireguard_config_content(config_path):
    # Placeholder: In reality, read the content of the config file
    # Ensure this function securely handles file paths
    if config_path and "clients" in config_path: # Basic sanity check
        return f"# Simulated WireGuard config for {config_path.split("/")[-1]}\n[Interface]\nPrivateKey = FAKE_PRIVATE_KEY\nAddress = 10.0.0.X/24\nDNS = 1.1.1.1\n\n[Peer]\nPublicKey = FAKE_SERVER_PUBLIC_KEY\nAllowedIPs = 0.0.0.0/0\nEndpoint = vpn.tarimtours.com:51820"
    return None

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered"}), 409

    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
    
    # For free trial, set an expiration date (e.g., 7 days from now)
    trial_duration = datetime.timedelta(days=7)
    expires_at = datetime.datetime.utcnow() + trial_duration

    # Simulate creating WireGuard user and getting config path
    wg_config_file_path = create_wireguard_user(email)

    new_user = User(
        email=email, 
        password_hash=hashed_password, 
        trial_expires_at=expires_at, 
        is_vip=False, 
        wg_config_path=wg_config_file_path
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully. Free trial activated."}), 201

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid email or password"}), 401

    # Check if trial has expired for non-VIP users
    if not user.is_vip and user.trial_expires_at and user.trial_expires_at < datetime.datetime.utcnow():
        return jsonify({"message": "Free trial has expired. Please upgrade to VIP."}), 403

    # Generate JWT token
    token_payload = {
        "user_id": user.id,
        "email": user.email,
        "is_vip": user.is_vip,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24) # Token expires in 24 hours
    }
    secret_key = app.config.get("SECRET_KEY", "default_secret_key_for_safety")
    token = jwt.encode(token_payload, secret_key, algorithm="HS256")

    return jsonify({
        "message": "Login successful", 
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "is_vip": user.is_vip,
            "trial_expires_at": user.trial_expires_at.isoformat() if user.trial_expires_at else None
        }
    }), 200
