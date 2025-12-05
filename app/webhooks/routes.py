import requests
from flask import current_app, jsonify, request

from app.extensions import db
from app.models import PayPalOrder, User
from app.webhooks import bp


def _paypal_access_token() -> str:
    client_id = current_app.config.get("PAYPAL_CLIENT_ID", "")
    client_secret = current_app.config.get("PAYPAL_CLIENT_SECRET", "")
    api_base = current_app.config.get(
        "PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com"
    )
    auth = (client_id, client_secret)
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = {"grant_type": "client_credentials"}
    resp = requests.post(
        f"{api_base}/v1/oauth2/token", headers=headers, data=data, auth=auth
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _verify_webhook(headers, body) -> bool:
    api_base = current_app.config.get("PAYPAL_API_BASE")
    webhook_id = current_app.config.get("PAYPAL_WEBHOOK_ID", "")
    if not webhook_id:
        # If no webhook ID configured, we can't verify, fail safe? or skip verification in dev?
        # For security, we should return False, but if user hasn't set it up yet, maybe log a warning.
        current_app.logger.warning("PAYPAL_WEBHOOK_ID not set, skipping verification")
        return False

    try:
        access = _paypal_access_token()
    except Exception as e:
        current_app.logger.error(f"Failed to get PayPal access token: {e}")
        return False

    payload = {
        "auth_algo": headers.get("PAYPAL-AUTH-ALGO", ""),
        "cert_url": headers.get("PAYPAL-CERT-URL", ""),
        "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID", ""),
        "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG", ""),
        "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME", ""),
        "webhook_id": webhook_id,
        "webhook_event": body,
    }

    try:
        resp = requests.post(
            f"{api_base}/v1/notifications/verify-webhook-signature",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access}",
            },
            json=payload,
        )
        return (
            resp.status_code == 200
            and resp.json().get("verification_status") == "SUCCESS"
        )
    except Exception as e:
        current_app.logger.error(f"Webhook verification error: {e}")
        return False


@bp.route("/paypal", methods=["POST"])
def paypal_webhook():
    event = request.get_json(silent=True) or {}

    # In dev mode we might want to skip verification if testing manually with curl
    if not current_app.debug:
        if not _verify_webhook(request.headers, event):
            return jsonify(
                {"status": "error", "message": "Webhook verification failed"}
            ), 400

    event_type = event.get("event_type", "")
    resource = event.get("resource", {})

    # Try to get order_id from resource
    # For CAPTURE.COMPLETED, resource.supplementary_data.related_ids.order_id
    order_id = (
        resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
    )

    # Fallback: check links for 'up' rel which usually points to order
    if not order_id:
        for link in resource.get("links", []) or []:
            if link.get("rel") == "up":
                # href: .../v2/checkout/orders/ID
                order_id = (link.get("href", "").rstrip("/").split("/") or [""])[-1]
                break

    # Fallback: custom_id (we put user_id there, not order id, so skip)
    # Fallback: id if it is the order itself (e.g. CHECKOUT.ORDER.APPROVED)
    if not order_id and event_type.startswith("CHECKOUT.ORDER"):
        order_id = resource.get("id")

    if not order_id:
        current_app.logger.error(
            f"Could not determine Order ID from event {event_type}"
        )
        return jsonify({"status": "ignored", "message": "Order ID not found"}), 200

    order = PayPalOrder.query.filter_by(paypal_order_id=order_id).first()
    if not order:
        current_app.logger.warning(f"PayPal Order {order_id} not found in DB")
        return jsonify({"status": "error", "message": "Order not found"}), 404

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        # Refresh state
        db.session.refresh(order)

        if order.status != "COMPLETED":
            order.status = "COMPLETED"

            # Credit the user
            user = User.query.get(order.user_id)
            if user:
                user.account_credits += order.credits_purchased
                current_app.logger.info(
                    f"Credited user {user.username} with {order.credits_purchased} credits via webhook."
                )

            db.session.commit()
        else:
            current_app.logger.info(
                f"Webhook: Order {order_id} already COMPLETED. Skipping credit."
            )

        return jsonify({"status": "ok", "message": "Processed"}), 200

    if event_type == "PAYMENT.CAPTURE.REFUNDED":
        if order.status == "COMPLETED":
            order.status = "REFUNDED"
            # Optionally deduct credits? For now just mark status.
            # To allow re-purchase or manual intervention.
            current_app.logger.info(f"Order {order_id} was refunded.")
            db.session.commit()
        return jsonify({"status": "ok", "message": "Refund noted"}), 200

    if event_type == "PAYMENT.CAPTURE.DENIED":
        order.status = "DENIED"
        db.session.commit()
        return jsonify({"status": "ok", "message": "Denied noted"}), 200

    return jsonify({"status": "ok", "event_type": event_type}), 200
