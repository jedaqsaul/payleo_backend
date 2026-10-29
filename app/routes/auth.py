from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from app.extensions import db  # noqa: F401
from app.models.user import User
from app.utils.errors import ApiError
from app.utils.validation import require_fields, validate_email

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["name", "email", "password"])

    email = validate_email(data.get("email"))
    name = str(data.get("name")).strip()
    password = data.get("password")

    if len(password) < 8:
        raise ApiError("Password must be at least 8 characters", 400)

    if User.query.filter_by(email=email).first():
        raise ApiError("Email is already registered", 409)

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "access_token": token}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["email", "password"])

    email = validate_email(data.get("email"))
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise ApiError("Invalid email or password", 401)

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "access_token": token}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user:
        raise ApiError("User not found", 404)
    return jsonify({"user": user.to_dict()}), 200
