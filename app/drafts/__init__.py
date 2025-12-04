from flask import Blueprint

bp = Blueprint("drafts", __name__)

from app.drafts import routes  # noqa: E402, F401  # noqa: E402, F401
