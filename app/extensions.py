from flask_babel import Babel
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_apscheduler import APScheduler
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
babel = Babel()
migrate = Migrate()
mail = Mail()
scheduler = APScheduler()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)
