from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Notification
from app.notifications import bp


@bp.route("/")
@login_required
def index():
    notifications = (
        current_user.notifications.order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template("notifications/index.html", notifications=notifications)


@bp.route("/mark_read/<int:notification_id>")
@login_required
def mark_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first()
    if notification:
        notification.is_read = True
        db.session.commit()
        if notification.link:
            return redirect(notification.link)
    return redirect(url_for("notifications.index"))


@bp.route("/mark_all_read")
@login_required
def mark_all_read():
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).all()
    for n in unread_notifications:
        n.is_read = True
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications.index"))
