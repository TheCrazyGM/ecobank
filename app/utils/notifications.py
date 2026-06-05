from flask import current_app
from app.extensions import db
from app.models import Notification


def create_notification(user_id, message, link=None, type="info"):
    """Creates a notification for a user."""
    try:
        notification = Notification(
            user_id=user_id, message=message, link=link, type=type
        )
        db.session.add(notification)
        db.session.commit()
        current_app.logger.info(f"Notification created for user {user_id}: {message}")
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create notification: {e}")
        return False
