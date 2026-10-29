from decimal import Decimal

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.invoice import Invoice, InvoiceStatus
from app.services.invoice_status import refresh_overdue_for_user

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/summary/")
@jwt_required()
def summary():
    user_id = int(get_jwt_identity())
    refresh_overdue_for_user(user_id)

    invoices = Invoice.query.filter_by(user_id=user_id).all()

    total_invoices = len(invoices)
    paid = [i for i in invoices if i.status == InvoiceStatus.PAID]
    outstanding = [i for i in invoices if i.status in (InvoiceStatus.SENT, InvoiceStatus.OVERDUE)]
    overdue = [i for i in invoices if i.status == InvoiceStatus.OVERDUE]

    total_invoiced = sum((i.total for i in invoices), Decimal("0.00"))
    total_paid = sum((i.total for i in paid), Decimal("0.00"))
    total_outstanding = sum((i.total for i in outstanding), Decimal("0.00"))

    return jsonify({
        "total_invoices": total_invoices,
        "paid_invoices": len(paid),
        "outstanding_invoices": len(outstanding),
        "overdue_invoices": len(overdue),
        "total_invoiced": str(total_invoiced),
        "total_paid": str(total_paid),
        "total_outstanding": str(total_outstanding),
    }), 200
