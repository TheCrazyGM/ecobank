from flask_babel import Babel
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_apscheduler import APScheduler

db = SQLAlchemy()
login_manager = LoginManager()
babel = Babel()
migrate = Migrate()
mail = Mail()
scheduler = APScheduler()
