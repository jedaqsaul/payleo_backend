from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.product import Product
from app.utils.errors import ApiError
from app.utils.validation import require_fields, parse_decimal
from app.utils.pagination import paginate_query

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


def _current_user_id():
    return int(get_jwt_identity())


def _get_owned_product(product_id):
    product = db.session.get(Product, product_id)
    if not product or product.user_id != _current_user_id():
        raise ApiError("Product not found", 404)
    return product


@products_bp.get("/")
@jwt_required()
def list_products():
    query = Product.query.filter_by(user_id=_current_user_id())

    search = request.args.get("search")
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(Product.name.ilike(like), Product.description.ilike(like)))

    query = query.order_by(Product.created_at.desc())
    pagination, meta = paginate_query(query)

    return jsonify({
        "products": [p.to_dict() for p in pagination.items],
        "pagination": meta,
    }), 200


@products_bp.post("/")
@jwt_required()
def create_product():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["name", "unit_price"])

    unit_price = parse_decimal(data.get("unit_price"), "unit_price", min_value=0)

    product = Product(
        user_id=_current_user_id(),
        name=str(data.get("name")).strip(),
        description=data.get("description"),
        unit_price=unit_price,
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"product": product.to_dict()}), 201


@products_bp.get("/<int:product_id>/")
@jwt_required()
def get_product(product_id):
    product = _get_owned_product(product_id)
    return jsonify({"product": product.to_dict()}), 200


def _apply_product_updates(product, data):
    if "name" in data:
        if not data.get("name"):
            raise ApiError("Name cannot be empty", 400)
        product.name = str(data["name"]).strip()
    if "description" in data:
        product.description = data["description"]
    if "unit_price" in data:
        product.unit_price = parse_decimal(data["unit_price"], "unit_price", min_value=0)


@products_bp.put("/<int:product_id>/")
@products_bp.patch("/<int:product_id>/")
@jwt_required()
def update_product(product_id):
    product = _get_owned_product(product_id)
    data = request.get_json(silent=True) or {}
    _apply_product_updates(product, data)
    db.session.commit()
    return jsonify({"product": product.to_dict()}), 200


@products_bp.delete("/<int:product_id>/")
@jwt_required()
def delete_product(product_id):
    product = _get_owned_product(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"}), 200
