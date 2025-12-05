from flask import Blueprint
from . import routes as routes  # Fix F401

bp = Blueprint("api", __name__)
