from flask import Blueprint

bp = Blueprint("drafts", __name__)

from app.drafts import routes
