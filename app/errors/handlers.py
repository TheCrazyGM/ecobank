from flask import render_template
from app.extensions import db
from app.errors import bp


@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()  # Ensure DB session is clean
    return render_template("errors/500.html"), 500
