from datetime import UTC

from flask import Flask, current_app, request
from flask_babel import gettext as _
from flask_babel import ngettext
from flask_login import current_user

from app.extensions import babel, db, login_manager, mail, migrate, scheduler
from app.utils.markdown_render import render_markdown
from config import Config


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
    # Initialize cache and limiter
    from app.extensions import cache, limiter

    cache.init_app(app)
    limiter.init_app(app)

    # Initialize Scheduler
    import os  # Move import os here to fix F823

    # Only run scheduler in production or if explicitly enabled, to avoid double-runs in debug reloader
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        try:
            import atexit
            import fcntl

            lock_file = open("/tmp/ecobank_scheduler.lock", "w")
            fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # If we acquire the lock, we are the designated scheduler worker
            scheduler.init_app(app)
            from app.tasks import (
                backup_database,
                cleanup_draft_versions,
                run_paypal_maintenance,
                update_ecobank_price_snapshot,
            )  # Import function directly

            scheduler.start()

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

            scheduler.add_job(
                id="update_ecobank_price_snapshot",
                func=update_ecobank_price_snapshot,
                trigger="interval",
                hours=1,
            )

            atexit.register(lambda: scheduler.shutdown(wait=False))
            # Lock is automatically released when the process exits and file identifier is closed

        except OSError:
            # Failed to acquire lock, another worker is running the scheduler
            pass

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
        from datetime import datetime

        return {"now": datetime.now(UTC)}

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

    # User-facing name is "circle"; the blueprint id stays "groups" (and the
    # Group models / group_id columns are unchanged) so url_for("groups.*")
    # keeps working. Old /groups/* URLs 301 to /circles/* via app.redirects.
    app.register_blueprint(groups_bp, url_prefix="/circles")

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

    # Search-engine indexing policy: noindex everything except public pages
    from app import security_headers

    security_headers.init_app(app)

    # 301s for URLs that moved (e.g. /groups/* -> /circles/*)
    from app import redirects

    redirects.init_app(app)

    # Activate "Under Attack" Mode (Browser Check Middleware)
    # Disabled to avoid Google Safe Browsing redirect/cloaking flags
    # from app.middleware import BrowserCheckMiddleware
    from werkzeug.middleware.proxy_fix import ProxyFix

    # Order: Request -> ProxyFix -> Flask
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    # app.wsgi_app = BrowserCheckMiddleware(app.wsgi_app)

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

        # Also log to stdout so Gunicorn/Docker picks it up
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("EcoBank startup")

        app.logger.setLevel(logging.INFO)
        app.logger.info("EcoBank startup")

    from app.cli import cleanup_spam

    app.cli.add_command(cleanup_spam)

    return app
