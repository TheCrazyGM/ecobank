from flask import Blueprint

bp = Blueprint("notifications", __name__)

from . import routes as routes  # noqa: E402, F401
