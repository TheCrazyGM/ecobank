import requests
from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import PayPalOrder
from app.paypal import bp


def get_paypal_access_token():
    client_id = current_app.config["PAYPAL_CLIENT_ID"]
    client_secret = current_app.config["PAYPAL_CLIENT_SECRET"]
    api_base = current_app.config["PAYPAL_API_BASE"]

    if not client_id or not client_secret:
        raise ValueError("PayPal credentials not configured")

    auth = (client_id, client_secret)
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = {"grant_type": "client_credentials"}

    response = requests.post(
        f"{api_base}/v1/oauth2/token", headers=headers, data=data, auth=auth
    )
    response.raise_for_status()
    return response.json()["access_token"]


@bp.route("/create-order", methods=["POST"])
@login_required
def create_order():
    try:
        data = request.get_json()
        credits_qty = int(data.get("quantity", 1))
        if credits_qty < 1:
            credits_qty = 1

        unit_price = current_app.config.get("CREDIT_PRICE_USD", 3.00)
        total_amount = round(unit_price * credits_qty, 2)

        access_token = get_paypal_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        order_payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "USD",
                        "value": str(total_amount),
                    },
                    "description": f"{credits_qty} Account Creation Credit(s)",
                    "custom_id": str(
                        current_user.id
                    ),  # Pass user ID in metadata if needed
                }
            ],
        }

        api_base = current_app.config["PAYPAL_API_BASE"]
        response = requests.post(
            f"{api_base}/v2/checkout/orders", json=order_payload, headers=headers
        )
        response.raise_for_status()
        order_data = response.json()

        # Save pending order
        new_order = PayPalOrder(
            user_id=current_user.id,
            paypal_order_id=order_data["id"],
            amount=total_amount,
            credits_purchased=credits_qty,
            status="CREATED",
        )
        db.session.add(new_order)
        db.session.commit()

        return jsonify(order_data)

    except Exception as e:
        current_app.logger.exception("Error creating PayPal order")
        return jsonify({"error": str(e)}), 500


@bp.route("/capture-order/<order_id>", methods=["POST"])
@login_required
def capture_order(order_id):
    try:
        # Verify order exists and belongs to user (or just exists if we trust the ID coming back matches logic)
        # Security: Ensure we only capture orders we know about.
        order = PayPalOrder.query.filter_by(paypal_order_id=order_id).first()
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Re-fetch order to ensure we have the latest status (simple check)
        db.session.refresh(order)

        if order.status == "COMPLETED":
            return jsonify(
                {"status": "COMPLETED", "message": "Order already completed"}
            )

        access_token = get_paypal_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        api_base = current_app.config["PAYPAL_API_BASE"]
        response = requests.post(
            f"{api_base}/v2/checkout/orders/{order_id}/capture", headers=headers
        )
        response.raise_for_status()
        capture_data = response.json()

        if capture_data["status"] == "COMPLETED":
            return jsonify(capture_data)
        else:
            return jsonify(capture_data), 400

    except Exception as e:
        current_app.logger.exception("Error capturing PayPal order")
        return jsonify({"error": str(e)}), 500
