from flask import Flask, current_app, request
from flask_babel import gettext as _
from flask_babel import ngettext
from flask_login import current_user

from app.extensions import babel, db, login_manager, migrate
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

    # Ensure i18n helpers are available in templates (Ecofront pattern)
    app.jinja_env.add_extension("jinja2.ext.i18n")
    app.jinja_env.globals.update(_=_, gettext=_, ngettext=ngettext)

    # Register filters
    app.jinja_env.filters["markdown"] = render_markdown

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

    return app
