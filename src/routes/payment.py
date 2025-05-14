# /home/ubuntu/vpn_backend/src/routes/payment.py
import os
import stripe
from flask import Blueprint, request, jsonify, redirect
from src.models.user import db, User
from src.routes.auth import token_required # Assuming token_required is in auth.py and accessible
from ..app import app # To access app.config for SECRET_KEY and other configs

payment_bp = Blueprint("payment", __name__)

# Configure Stripe API key
# In a real app, use environment variables for STRIPE_SECRET_KEY
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_YOUR_STRIPE_SECRET_KEY") # Replace with your test secret key

# Placeholder for your Stripe Price ID (e.g., for the VIP plan)
# This would be created in your Stripe Dashboard
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "price_YOUR_VIP_PLAN_PRICE_ID") # Replace with your actual test Price ID

# Endpoint to create a Stripe Checkout Session
@payment_bp.route("/payment/create-checkout-session", methods=["POST"])
@token_required
def create_checkout_session(current_user):
    # For simplicity, we assume the user is trying to upgrade to a single VIP plan
    # In a more complex app, you might pass a price_id or product_id from the frontend
    try:
        # Create a new Checkout Session
        # The success_url and cancel_url should be frontend routes that handle these states
        # For local development, these might be http://localhost:3000/payment/success etc.
        # For deployed app, use the actual deployed frontend URLs.
        # Ensure your frontend application has these routes.
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000") # Get from env or default

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": STRIPE_PRICE_ID,
                    "quantity": 1,
                },
            ],
            mode="subscription", # For recurring payments
            success_url=f"{FRONTEND_URL}/dashboard?payment_success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/pricing?payment_cancelled=true",
            client_reference_id=str(current_user.id), # Pass user ID to identify user in webhook
            # If you want to create a Stripe customer and save it to your User model:
            customer_email=current_user.email, # Pre-fill email
            # To create a customer and save the ID, you might do this:
            # customer_creation="always", # Creates a customer object in Stripe
        )
        # If customer_creation="always", you can retrieve customer ID via events or session object
        # and save it to your User model (user.stripe_customer_id = session.customer)

        # Return the session ID or URL to the frontend
        # Using session.url is simpler as it directly redirects the user
        return jsonify({"checkout_url": checkout_session.url, "session_id": checkout_session.id}), 200

    except Exception as e:
        app.logger.error(f"Stripe Checkout Session error: {str(e)}")
        return jsonify(error=str(e)), 403

# Stripe Webhook Handler
# This endpoint must be publicly accessible for Stripe to send events.
# Remember to set up this webhook endpoint in your Stripe Dashboard (Developers > Webhooks).
# For local testing, use the Stripe CLI: `stripe listen --forward-to localhost:5000/api/payment/webhook`
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_YOUR_WEBHOOK_SECRET") # Replace with your webhook signing secret

@payment_bp.route("/payment/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        app.logger.error(f"Webhook ValueError: {str(e)}")
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        app.logger.error(f"Webhook SignatureVerificationError: {str(e)}")
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        app.logger.error(f"Webhook general error: {str(e)}")
        return jsonify({"error": "Webhook processing error"}), 500

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        app.logger.info(f"Checkout session completed: {session}")
        
        client_reference_id = session.get("client_reference_id")
        stripe_customer_id = session.get("customer")
        stripe_subscription_id = session.get("subscription")

        if not client_reference_id:
            app.logger.error("Webhook error: client_reference_id missing in checkout.session.completed event")
            return jsonify({"error": "Client reference ID missing"}), 400

        user = User.query.get(int(client_reference_id))
        if user:
            user.is_vip = True
            user.trial_expires_at = None # VIPs don't have trial expirations
            if stripe_customer_id:
                user.stripe_customer_id = stripe_customer_id
            if stripe_subscription_id:
                user.stripe_subscription_id = stripe_subscription_id
            
            # Placeholder: Update WireGuard config to remove limitations
            # This would involve interacting with wg-easy or your VPN management tool
            app.logger.info(f"User {user.email} (ID: {user.id}) upgraded to VIP.")
            # Example: update_wg_user_to_vip(user.email)
            
            db.session.commit()
            app.logger.info(f"User {user.id} successfully upgraded to VIP and Stripe info saved.")
        else:
            app.logger.error(f"Webhook error: User not found for client_reference_id: {client_reference_id}")
            return jsonify({"error": "User not found"}), 404

    elif event["type"] == "invoice.payment_succeeded":
        # Handle successful recurring payment if needed (e.g., extend subscription)
        # For simple subscription, Stripe handles this, but you might log it or update internal records.
        session = event["data"]["object"]
        app.logger.info(f"Invoice payment succeeded: {session}")
        # subscription_id = session.get("subscription")
        # customer_id = session.get("customer")
        # user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
        # if user:
        #    app.logger.info(f"Subscription for user {user.email} (ID: {user.id}) successfully renewed.")
        # else:
        #    app.logger.warning(f"Invoice payment succeeded for unknown subscription: {subscription_id}")
        pass

    elif event["type"] == "invoice.payment_failed":
        # Handle failed recurring payment (e.g., notify user, downgrade account after grace period)
        session = event["data"]["object"]
        app.logger.warning(f"Invoice payment failed: {session}")
        # subscription_id = session.get("subscription")
        # customer_id = session.get("customer")
        # user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
        # if user:
        #    app.logger.warning(f"Subscription payment failed for user {user.email} (ID: {user.id}). Action may be required.")
            # Implement logic: notify user, set grace period, eventually downgrade.
        # else:
        #    app.logger.warning(f"Invoice payment failed for unknown subscription: {subscription_id}")
        pass
    
    # ... handle other event types as needed

    else:
        app.logger.info(f"Unhandled event type {event['type']}")

    return jsonify({"received": True}), 200

