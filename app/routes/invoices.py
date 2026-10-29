from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.utils.errors import ApiError
from app.utils.validation import require_fields, parse_decimal, parse_date
from app.utils.pagination import paginate_query
from app.services.invoice_calculator import build_items, compute_totals
from app.services.invoice_numbering import generate_invoice_number
from app.services.invoice_status import (
    transition_status,
    mark_paid as svc_mark_paid,
    refresh_overdue_status,
    refresh_overdue_for_user,
    parse_status,
)
from app.services.pdf_generator import generate_invoice_pdf
from app.models.user import User

invoices_bp = Blueprint("invoices", __name__, url_prefix="/api/invoices")


def _current_user_id():
    return int(get_jwt_identity())


def _get_owned_invoice(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice or invoice.user_id != _current_user_id():
        raise ApiError("Invoice not found", 404)
    return invoice


def _get_owned_customer(customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer or customer.user_id != _current_user_id():
        raise ApiError("Customer not found", 400)
    return customer


@invoices_bp.get("/")
@jwt_required()
def list_invoices():
    user_id = _current_user_id()
    refresh_overdue_for_user(user_id)

    query = Invoice.query.filter_by(user_id=user_id)

    status = request.args.get("status")
    if status:
        query = query.filter(Invoice.status == parse_status(status))

    customer_id = request.args.get("customer_id")
    if customer_id:
        query = query.filter(Invoice.customer_id == int(customer_id))

    issue_date = request.args.get("issue_date")
    if issue_date:
        query = query.filter(Invoice.issue_date == parse_date(issue_date, "issue_date"))

    due_date = request.args.get("due_date")
    if due_date:
        query = query.filter(Invoice.due_date == parse_date(due_date, "due_date"))

    search = request.args.get("search")
    if search:
        like = f"%{search}%"
        query = query.join(Customer).filter(
            db.or_(Invoice.invoice_number.ilike(like), Customer.name.ilike(like))
        )

    query = query.order_by(Invoice.created_at.desc())
    pagination, meta = paginate_query(query)

    return jsonify({
        "invoices": [inv.to_dict(include_items=False) for inv in pagination.items],
        "pagination": meta,
    }), 200


@invoices_bp.post("/")
@jwt_required()
def create_invoice():
    user_id = _current_user_id()
    data = request.get_json(silent=True) or {}
    require_fields(data, ["customer_id", "issue_date", "due_date", "items"])

    customer = _get_owned_customer(data.get("customer_id"))

    issue_date = parse_date(data.get("issue_date"), "issue_date")
    due_date = parse_date(data.get("due_date"), "due_date")
    if due_date < issue_date:
        raise ApiError("due_date cannot be earlier than issue_date", 400)

    tax = parse_decimal(data.get("tax", "0"), "tax", min_value=0)
    items = build_items(data.get("items"))
    subtotal, tax, total = compute_totals(items, tax)

    try:
        invoice_number = generate_invoice_number(user_id)
        invoice = Invoice(
            user_id=user_id,
            customer_id=customer.id,
            invoice_number=invoice_number,
            issue_date=issue_date,
            due_date=due_date,
            status=InvoiceStatus.DRAFT,
            subtotal=subtotal,
            tax=tax,
            total=total,
            notes=data.get("notes"),
        )
        invoice.items = items
        db.session.add(invoice)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"invoice": invoice.to_dict()}), 201


@invoices_bp.get("/<int:invoice_id>/")
@jwt_required()
def get_invoice(invoice_id):
    invoice = _get_owned_invoice(invoice_id)
    refresh_overdue_status(invoice)
    return jsonify({"invoice": invoice.to_dict()}), 200


@invoices_bp.put("/<int:invoice_id>/")
@invoices_bp.patch("/<int:invoice_id>/")
@jwt_required()
def update_invoice(invoice_id):
    invoice = _get_owned_invoice(invoice_id)
    data = request.get_json(silent=True) or {}

    if invoice.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
        raise ApiError(f"Cannot edit an invoice that is {invoice.status.value}", 409)

    try:
        if "customer_id" in data:
            customer = _get_owned_customer(data["customer_id"])
            invoice.customer_id = customer.id

        if "issue_date" in data:
            invoice.issue_date = parse_date(data["issue_date"], "issue_date")
        if "due_date" in data:
            invoice.due_date = parse_date(data["due_date"], "due_date")
        if invoice.due_date < invoice.issue_date:
            raise ApiError("due_date cannot be earlier than issue_date", 400)

        if "notes" in data:
            invoice.notes = data["notes"]

        recompute = False
        tax = invoice.tax
        if "tax" in data:
            tax = parse_decimal(data["tax"], "tax", min_value=0)
            recompute = True

        if "items" in data:
            items = build_items(data["items"])
            invoice.items = items
            recompute = True

        if recompute:
            subtotal, tax, total = compute_totals(invoice.items, tax)
            invoice.subtotal = subtotal
            invoice.tax = tax
            invoice.total = total

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"invoice": invoice.to_dict()}), 200


@invoices_bp.delete("/<int:invoice_id>/")
@jwt_required()
def delete_invoice(invoice_id):
    invoice = _get_owned_invoice(invoice_id)
    if invoice.status == InvoiceStatus.PAID:
        raise ApiError("Cannot delete a paid invoice", 409)
    db.session.delete(invoice)
    db.session.commit()
    return jsonify({"message": "Invoice deleted"}), 200


@invoices_bp.post("/<int:invoice_id>/status/")
@jwt_required()
def change_status(invoice_id):
    invoice = _get_owned_invoice(invoice_id)
    data = request.get_json(silent=True) or {}
    require_fields(data, ["status"])
    new_status = parse_status(data["status"])
    transition_status(invoice, new_status)
    return jsonify({"invoice": invoice.to_dict()}), 200


@invoices_bp.post("/<int:invoice_id>/mark-paid/")
@jwt_required()
def mark_paid(invoice_id):
    invoice = _get_owned_invoice(invoice_id)
    svc_mark_paid(invoice)
    return jsonify({"invoice": invoice.to_dict()}), 200


@invoices_bp.get("/<int:invoice_id>/pdf/")
@jwt_required()
def download_pdf(invoice_id):
    invoice = _get_owned_invoice(invoice_id)
    user = db.session.get(User, _current_user_id())
    pdf_bytes = generate_invoice_pdf(invoice, user)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"},
    )
