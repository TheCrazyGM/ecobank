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


def process_refund(paypal_order_id: str):
    """
    Processes a refund for a PayPal order.
    Deducts credits if available, otherwise marks for audit.
    """
    try:
        order = PayPalOrder.query.filter_by(paypal_order_id=paypal_order_id).first()
        if not order:
            return False, "Order not found"

        db.session.refresh(order)

        if order.status == "COMPLETED":
            user = User.query.get(order.user_id)
            if not user:
                # Weird edge case, user gone but order exists
                current_app.logger.error(
                    f"User {order.user_id} not found for refunding order {paypal_order_id}"
                )
                order.status = "REFUND_AUDIT"
                db.session.commit()
                return True, "User missing, marked for audit"

            if user.account_credits >= order.credits_purchased:
                user.account_credits -= order.credits_purchased
                order.status = "REFUNDED"
                current_app.logger.info(
                    f"Refunded order {paypal_order_id}. Deducted {order.credits_purchased} credits from {user.username}"
                )
            else:
                # Not enough credits to deduct!
                order.status = "REFUND_AUDIT"
                current_app.logger.warning(
                    f"Refund Audit: User {user.username} has insufficient credits ({user.account_credits}) to refund order {paypal_order_id} ({order.credits_purchased})"
                )

            db.session.commit()
            return True, f"Processed refund. Status: {order.status}"

        elif order.status in ["REFUNDED", "REFUND_AUDIT"]:
            return True, "Already refunded"

        else:
            # Maybe it was never completed? Just mark denied/refunded?
            order.status = "REFUNDED"
            db.session.commit()
            return True, "Marked REFUNDED (was not COMPLETED)"

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error processing refund for {paypal_order_id}")
        return False, str(e)
