from flask import Blueprint

bp = Blueprint("api", __name__)

from . import routes as routes  # noqa: E402, F401
