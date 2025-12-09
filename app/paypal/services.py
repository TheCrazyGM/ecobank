from flask import current_app
from app.extensions import db
from app.models import PayPalOrder, User


def fulfill_order(paypal_order_id: str):
    """
    Idempotently fulfills a PayPal order.
    Grants credits only if the order is not already completed.
    Returns: (success: bool, message: str)
    """
    try:
        # Lock row if possible, or rely on GIL/atomic commit for simple robust check
        order = PayPalOrder.query.filter_by(paypal_order_id=paypal_order_id).first()

        if not order:
            return False, "Order not found"

        # Explicit refresh to get latest state
        db.session.refresh(order)

        if order.status == "COMPLETED":
            return True, "Order already completed"

        # Mark completed
        order.status = "COMPLETED"

        # Grant credits
        user = User.query.get(order.user_id)
        if user:
            user.account_credits += order.credits_purchased
            current_app.logger.info(
                f"Order {paypal_order_id} fulfilled. Credited user {user.username} with {order.credits_purchased} credits."
            )
        else:
            current_app.logger.warning(
                f"Order {paypal_order_id} fulfilled but User {order.user_id} not found."
            )

        db.session.commit()
        return True, "Credits granted"

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error fulfilling order {paypal_order_id}")
        return False, str(e)
