from app.extensions import db, scheduler
from app.models import PayPalOrder
from datetime import datetime, timedelta, timezone
import logging


def run_paypal_maintenance():
    """
    Scheduled task to:
    1. Mark CREATED orders as EXPIRED if older than 24 hours.
    2. Hard delete EXPIRED/FAILED/DENIED orders older than 30 days.
    """
    # Use app context because we access DB
    from flask import current_app

    app = scheduler.app or current_app
    with app.app_context():
        now = datetime.now(timezone.utc)
        expiration_time = now - timedelta(hours=24)
        deletion_time = now - timedelta(days=30)

        # 1. Expire old pending orders
        old_orders = PayPalOrder.query.filter(
            PayPalOrder.status == "CREATED", PayPalOrder.created_at < expiration_time
        ).all()

        expired_count = 0
        for order in old_orders:
            order.status = "EXPIRED"
            expired_count += 1

        # 2. Hard delete old failed/expired orders
        orders_to_delete = PayPalOrder.query.filter(
            PayPalOrder.status.in_(["EXPIRED", "FAILED", "DENIED"]),
            PayPalOrder.created_at < deletion_time,
        ).all()

        deleted_count = 0
        for order in orders_to_delete:
            db.session.delete(order)
            deleted_count += 1

        if expired_count > 0 or deleted_count > 0:
            db.session.commit()
            logging.info(
                f"PayPal Maintenance: Expired {expired_count} orders, Deleted {deleted_count} old orders."
            )
        else:
            logging.info("PayPal Maintenance: No actions needed.")


def cleanup_draft_versions():
    """
    Scheduled task to remove version history for published drafts.
    """
    from flask import current_app
    from app.models import Draft, DraftVersion

    app = scheduler.app or current_app
    with app.app_context():
        # Find all published drafts
        published_drafts = Draft.query.filter_by(status="published").all()

        cleanup_count = 0
        version_count = 0

        for draft in published_drafts:
            # Delete versions for this draft
            deleted = DraftVersion.objects(draft_id=draft.id).delete()
            if deleted > 0:
                cleanup_count += 1
                version_count += deleted

        if version_count > 0:
            logging.info(
                f"Draft Cleanup: Removed {version_count} versions from {cleanup_count} published drafts."
            )
        else:
            logging.info("Draft Cleanup: No versions to clean up.")
