from decimal import Decimal

from app.extensions import db


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)

    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    quantity = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("1"))
    unit_price = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    line_total = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_invoice_items_quantity_positive"),
        db.CheckConstraint("unit_price >= 0", name="ck_invoice_items_unit_price_non_negative"),
    )

    def compute_line_total(self):
        self.line_total = (Decimal(self.quantity) * Decimal(self.unit_price)).quantize(Decimal("0.01"))
        return self.line_total

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "line_total": str(self.line_total),
        }

    def __repr__(self):
        return f"<InvoiceItem {self.name} x{self.quantity}>"
