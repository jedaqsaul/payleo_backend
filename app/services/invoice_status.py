from datetime import datetime, timezone, date

from app.extensions import db
from app.models.invoice import Invoice, InvoiceStatus, ALLOWED_TRANSITIONS
from app.utils.errors import ApiError


def transition_status(invoice: Invoice, new_status: InvoiceStatus, commit=True):
    """Move an invoice to a new status, enforcing the allowed-transition graph."""
    if new_status == invoice.status:
        return invoice

    allowed = ALLOWED_TRANSITIONS.get(invoice.status, set())
    if new_status not in allowed:
        raise ApiError(
            f"Cannot transition invoice from {invoice.status.value} to {new_status.value}",
            409,
        )

    invoice.status = new_status
    if new_status == InvoiceStatus.PAID:
        invoice.paid_at = datetime.now(timezone.utc)

    if commit:
        db.session.commit()
    return invoice


def mark_paid(invoice: Invoice):
    return transition_status(invoice, InvoiceStatus.PAID)


def refresh_overdue_status(invoice: Invoice, commit=True):
    """Promote SENT invoices past their due date to OVERDUE. Idempotent, no-op otherwise."""
    if invoice.status == InvoiceStatus.SENT and invoice.due_date < date.today():
        invoice.status = InvoiceStatus.OVERDUE
        if commit:
            db.session.commit()
    return invoice


def refresh_overdue_for_user(user_id, commit=True):
    """Bulk-promote all of a user's SENT-but-late invoices to OVERDUE."""
    stale = Invoice.query.filter(
        Invoice.user_id == user_id,
        Invoice.status == InvoiceStatus.SENT,
        Invoice.due_date < date.today(),
    ).all()
    for invoice in stale:
        invoice.status = InvoiceStatus.OVERDUE
    if stale and commit:
        db.session.commit()
    return stale


def parse_status(value):
    if isinstance(value, InvoiceStatus):
        return value
    try:
        return InvoiceStatus(str(value).upper())
    except ValueError:
        raise ApiError(f"Invalid status: {value}", 400)
