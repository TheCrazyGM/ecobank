from flask import Blueprint

bp = Blueprint("paypal", __name__)

from app.paypal import routes
