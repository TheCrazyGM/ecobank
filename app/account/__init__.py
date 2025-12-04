from flask import Blueprint

bp = Blueprint("account", __name__)

from app.account import routes  # noqa: E402, F401  # noqa: E402, F401
