from flask import Blueprint
from . import routes as routes  # Fix F401

bp = Blueprint("notifications", __name__)
