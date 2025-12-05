from app.extensions import db, scheduler
from app.models import PayPalOrder
from datetime import datetime, timedelta, timezone
import logging


def cleanup_pending_orders():
    """
    Scheduled task to find PayPal orders that are in CREATED state for too long
    and mark them as FAILED or EXPIRED.
    """
    # Use app context because we access DB
    with scheduler.app.app_context():
        expiration_time = datetime.now(timezone.utc) - timedelta(hours=24)

        # Find old pending orders
        old_orders = PayPalOrder.query.filter(
            PayPalOrder.status == "CREATED", PayPalOrder.created_at < expiration_time
        ).all()

        count = 0
        for order in old_orders:
            order.status = "EXPIRED"
            count += 1

        if count > 0:
            db.session.commit()
            logging.info(f"Scheduled Task: Expired {count} old PayPal orders.")
        else:
            logging.info("Scheduled Task: No expired orders found.")
