import os

from flask import Flask, jsonify

from app.extensions import db, migrate, jwt, cors
from app.utils.errors import register_error_handlers, ApiError


def create_app(config_object=None):
    app = Flask(__name__)

    if config_object is None:
        from config import get_config
        config_object = get_config()
    app.config.from_object(config_object)

    # Ensure the instance folder (for the default SQLite dev db) exists.
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///") and ":memory:" not in db_uri:
        db_path = db_uri.replace("sqlite:///", "", 1)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    register_error_handlers(app)

    # Import models so Flask-Migrate can detect them.
    from app import models  # noqa: F401

    from app.routes import register_blueprints
    register_blueprints(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @jwt.unauthorized_loader
    def unauthorized_callback(reason):
        return jsonify({"error": "Missing or invalid authorization token"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return jsonify({"error": "Invalid token"}), 422

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired"}), 401

    return app
