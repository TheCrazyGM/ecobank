import os
from datetime import timedelta

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))
TRANSLATIONS_DIR = os.path.join(basedir, "translations")


class Config:
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "1")
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI"
    ) or "sqlite:///" + os.path.join(basedir, "instance", "ecobank.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # i18n
    BABEL_DEFAULT_LOCALE = os.environ.get("BABEL_DEFAULT_LOCALE", "en")
    BABEL_SUPPORTED_LOCALES = ("en", "es")
    BABEL_TRANSLATION_DIRECTORIES = os.environ.get(
        "BABEL_TRANSLATION_DIRECTORIES", TRANSLATIONS_DIR
    )

    # Hive Account Creation
    HIVE_CLAIMER_ACCOUNT = os.environ.get("HIVE_CLAIMER_ACCOUNT")
    HIVE_CLAIMER_KEY = os.environ.get("HIVE_CLAIMER_KEY")
    HIVE_ENCRYPTION_KEY = os.environ.get("HIVE_ENCRYPTION_KEY")

    # PayPal
    PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET")
    PAYPAL_API_BASE = os.environ.get(
        "PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com"
    )
    # Cost per credit in USD
    CREDIT_PRICE_USD = 3.00
