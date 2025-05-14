# /home/ubuntu/vpn_backend/src/routes/user.py
from flask import Blueprint, request, jsonify, send_file
from functools import wraps
import jwt
import datetime
import io # For sending file content

from src.models.user import db, User
from ..app import app # To access app.config for SECRET_KEY
from .auth import get_wireguard_config_content # Re-use the placeholder from auth.py for now

user_bp = Blueprint("user", __name__)

# --- JWT Token Verification Decorator ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "x-access-token" in request.headers:
            token = request.headers["x-access-token"]
        
        if not token:
            return jsonify({"message": "Token is missing!"}), 401
        
        try:
            secret_key = app.config.get("SECRET_KEY", "default_secret_key_for_safety")
            data = jwt.decode(token, secret_key, algorithms=["HS256"])
            current_user = User.query.get(data["user_id"])
            if not current_user:
                return jsonify({"message": "Token is invalid or user not found!"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Token is invalid!"}), 401
        except Exception as e:
            return jsonify({"message": f"Token validation error: {str(e)}"}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@user_bp.route("/user/status", methods=["GET"])
@token_required
def get_user_status(current_user):
    # In a real app, you might fetch live bandwidth data here
    # For now, we return stored/placeholder data
    return jsonify({
        "email": current_user.email,
        "is_vip": current_user.is_vip,
        "trial_expires_at": current_user.trial_expires_at.isoformat() if current_user.trial_expires_at else None,
        "plan": "VIP Plan" if current_user.is_vip else "Free Trial",
        "status": "Active" if not current_user.trial_expires_at or current_user.trial_expires_at > datetime.datetime.utcnow() or current_user.is_vip else "Expired",
        "bandwidthUsed": "15.5 GB (Placeholder)", # Placeholder
        "bandwidthLimit": "Unlimited (VIP)" if current_user.is_vip else "5 GB (Trial - Placeholder)" # Placeholder
    }), 200

@user_bp.route("/user/config", methods=["GET"])
@token_required
def download_config(current_user):
    if not current_user.wg_config_path:
        return jsonify({"message": "No VPN configuration found for this user."}), 404

    # Placeholder: Simulate fetching config content
    config_content = get_wireguard_config_content(current_user.wg_config_path)

    if not config_content:
        return jsonify({"message": "Could not retrieve VPN configuration."}), 500

    # Create a file-like object in memory
    config_io = io.BytesIO(config_content.encode("utf-8"))
    
    # Determine filename
    filename = current_user.wg_config_path.split("/")[-1]
    if not filename.endswith(".conf"):
        filename = f"{current_user.email.split("@")[0]}.conf"

    return send_file(
        config_io,
        mimetype="text/plain",
        as_attachment=True,
        download_name=filename
    )

# Placeholder for VIP upgrade - to be triggered by payment webhook later
@user_bp.route("/user/upgrade_vip_placeholder", methods=["POST"]) # This is a placeholder route
@token_required
def upgrade_to_vip(current_user):
    if current_user.is_vip:
        return jsonify({"message": "User is already a VIP."}), 400
    
    current_user.is_vip = True
    current_user.trial_expires_at = None # VIPs don't have trial expirations
    # Potentially update WireGuard config to remove limitations here
    db.session.commit()
    return jsonify({"message": "User upgraded to VIP successfully."}), 200

