from flask import Flask, current_app, request
from flask_babel import gettext as _
from flask_babel import ngettext
from flask_login import current_user

from app.extensions import babel, db, login_manager, migrate, mail, scheduler
from config import Config
from app.utils.markdown_render import render_markdown


def get_locale():
    if current_user.is_authenticated and current_user.locale:
        return current_user.locale
    return request.accept_languages.best_match(
        current_app.config["BABEL_SUPPORTED_LOCALES"]
    )


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Initialize Scheduler
    import os  # Move import os here to fix F823

    # Only run scheduler in production or if explicitly enabled, to avoid double-runs in debug reloader
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        scheduler.init_app(app)
        from app.tasks import (
            run_paypal_maintenance,
            cleanup_draft_versions,
            backup_database,
        )  # Import function directly

        scheduler.start()

        # Add jobs here or via configuration
        scheduler.add_job(
            id="paypal_maintenance",
            func=run_paypal_maintenance,
            trigger="interval",
            hours=1,
        )

        scheduler.add_job(
            id="cleanup_draft_versions",
            func=cleanup_draft_versions,
            trigger="interval",
            hours=24,
        )

        scheduler.add_job(
            id="backup_database",
            func=backup_database,
            trigger="interval",
            hours=24,
        )

        import atexit

        atexit.register(lambda: scheduler.shutdown(wait=False))

        # Initialize MongoEngine

        from mongoengine import connect

        connect(host=app.config["MONGO_URI"])

        # Ensure i18n helpers are available in templates (Ecofront pattern)

    app.jinja_env.add_extension("jinja2.ext.i18n")
    app.jinja_env.globals.update(_=_, gettext=_, ngettext=ngettext)

    # Register filters
    app.jinja_env.filters["markdown"] = render_markdown

    # Context Processors
    @app.context_processor
    def inject_now():
        from datetime import datetime, timezone

        return {"now": datetime.now(timezone.utc)}

    login_manager.login_view = "auth.login"

    # Register blueprints
    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.account import bp as account_bp

    app.register_blueprint(account_bp, url_prefix="/account")

    from app.paypal import bp as paypal_bp

    app.register_blueprint(paypal_bp, url_prefix="/paypal")

    from app.groups import bp as groups_bp

    app.register_blueprint(groups_bp, url_prefix="/groups")

    from app.drafts import bp as drafts_bp

    app.register_blueprint(drafts_bp, url_prefix="/drafts")

    from app.admin import bp as admin_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.webhooks import bp as webhooks_bp

    app.register_blueprint(webhooks_bp, url_prefix="/webhooks")

    from app.api import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    from app.notifications import bp as notifications_bp

    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    from app.errors import bp as errors_bp

    app.register_blueprint(errors_bp)

    import os  # Ensure os is imported

    if not app.debug and not app.testing:
        import logging
        from logging.handlers import RotatingFileHandler

        if not os.path.exists("logs"):
            os.mkdir("logs")
        file_handler = RotatingFileHandler(
            "logs/ecobank.log", maxBytes=10240, backupCount=10
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("EcoBank startup")

    return app
