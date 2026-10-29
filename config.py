import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


def _bool_env(name, default="false"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def normalize_db_url(url):
    """Force the psycopg 3 driver for every PostgreSQL URL.

    Hosts hand out `postgres://` (Render/Heroku) or a bare `postgresql://`, and
    SQLAlchemy's default driver for the bare form changed between versions.
    Being explicit makes the app independent of that default.
    """
    if not url:
        return url
    for prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def _db_url(env_name, default):
    return normalize_db_url(os.environ.get(env_name) or default)


class Config:
    """Base configuration. All secrets must come from environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = _db_url(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'payleo.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "24"))
    )
    JWT_TOKEN_LOCATION = ["headers"]

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

    DEBUG = _bool_env("FLASK_DEBUG", "false")
    TESTING = False

    # Business/application settings
    DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "USD")
    INVOICE_NUMBER_PREFIX = os.environ.get("INVOICE_NUMBER_PREFIX", "INV-")
    INVOICE_NUMBER_PADDING = int(os.environ.get("INVOICE_NUMBER_PADDING", "6"))

    PAGINATION_DEFAULT_PAGE_SIZE = int(os.environ.get("PAGINATION_DEFAULT_PAGE_SIZE", "20"))
    PAGINATION_MAX_PAGE_SIZE = int(os.environ.get("PAGINATION_MAX_PAGE_SIZE", "100"))


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _db_url(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'payleo_dev.db')}"
    )


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _db_url("TEST_DATABASE_URL", "sqlite:///:memory:")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
