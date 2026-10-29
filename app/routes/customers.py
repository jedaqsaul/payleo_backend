from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.customer import Customer
from app.utils.errors import ApiError
from app.utils.validation import require_fields, validate_email
from app.utils.pagination import paginate_query

customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")


def _current_user_id():
    return int(get_jwt_identity())


def _get_owned_customer(customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer or customer.user_id != _current_user_id():
        raise ApiError("Customer not found", 404)
    return customer


@customers_bp.get("/")
@jwt_required()
def list_customers():
    query = Customer.query.filter_by(user_id=_current_user_id())

    search = request.args.get("search")
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(Customer.name.ilike(like), Customer.email.ilike(like)))

    query = query.order_by(Customer.created_at.desc())
    pagination, meta = paginate_query(query)

    return jsonify({
        "customers": [c.to_dict() for c in pagination.items],
        "pagination": meta,
    }), 200


@customers_bp.post("/")
@jwt_required()
def create_customer():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["name"])

    email = data.get("email")
    if email:
        email = validate_email(email)

    customer = Customer(
        user_id=_current_user_id(),
        name=str(data.get("name")).strip(),
        email=email,
        phone=data.get("phone"),
        address=data.get("address"),
    )
    db.session.add(customer)
    db.session.commit()
    return jsonify({"customer": customer.to_dict()}), 201


@customers_bp.get("/<int:customer_id>/")
@jwt_required()
def get_customer(customer_id):
    customer = _get_owned_customer(customer_id)
    return jsonify({"customer": customer.to_dict()}), 200


def _apply_customer_updates(customer, data):
    if "name" in data:
        if not data.get("name"):
            raise ApiError("Name cannot be empty", 400)
        customer.name = str(data["name"]).strip()
    if "email" in data:
        customer.email = validate_email(data["email"], required=False) if data["email"] else None
    if "phone" in data:
        customer.phone = data["phone"]
    if "address" in data:
        customer.address = data["address"]


@customers_bp.put("/<int:customer_id>/")
@customers_bp.patch("/<int:customer_id>/")
@jwt_required()
def update_customer(customer_id):
    customer = _get_owned_customer(customer_id)
    data = request.get_json(silent=True) or {}
    _apply_customer_updates(customer, data)
    db.session.commit()
    return jsonify({"customer": customer.to_dict()}), 200


@customers_bp.delete("/<int:customer_id>/")
@jwt_required()
def delete_customer(customer_id):
    customer = _get_owned_customer(customer_id)
    if customer.invoices.count() > 0:
        raise ApiError("Cannot delete a customer that has invoices", 409)
    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": "Customer deleted"}), 200
