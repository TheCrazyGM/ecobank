from flask import Blueprint

bp = Blueprint("paypal", __name__)

from app.paypal import routes  # noqa: E402, F401  # noqa: E402, F401
