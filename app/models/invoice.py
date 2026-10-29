from datetime import datetime, timezone, date
from decimal import Decimal
import enum

from app.extensions import db


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


# Allowed status transitions. Key = current status, value = set of allowed next statuses.
ALLOWED_TRANSITIONS = {
    InvoiceStatus.DRAFT: {InvoiceStatus.SENT, InvoiceStatus.CANCELLED},
    InvoiceStatus.SENT: {InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.OVERDUE},
    InvoiceStatus.OVERDUE: {InvoiceStatus.PAID, InvoiceStatus.CANCELLED},
    InvoiceStatus.PAID: set(),
    InvoiceStatus.CANCELLED: set(),
}


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)

    invoice_number = db.Column(db.String(50), nullable=False)

    issue_date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    due_date = db.Column(db.Date, nullable=False)

    status = db.Column(db.Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT, index=True)

    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    tax = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    notes = db.Column(db.Text, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    items = db.relationship(
        "InvoiceItem", backref="invoice", lazy="joined", cascade="all, delete-orphan", order_by="InvoiceItem.id"
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "invoice_number", name="uq_invoices_user_invoice_number"),
        db.CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_non_negative"),
        db.CheckConstraint("tax >= 0", name="ck_invoices_tax_non_negative"),
        db.CheckConstraint("total >= 0", name="ck_invoices_total_non_negative"),
    )

    def is_overdue(self):
        if self.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
            return False
        return self.due_date < date.today()

    def to_dict(self, include_items=True):
        data = {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "invoice_number": self.invoice_number,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status.value if isinstance(self.status, InvoiceStatus) else self.status,
            "subtotal": str(self.subtotal),
            "tax": str(self.tax),
            "total": str(self.total),
            "notes": self.notes,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "is_overdue": self.is_overdue(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data

    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"
