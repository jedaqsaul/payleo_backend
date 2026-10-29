from decimal import Decimal

from app.models.invoice_item import InvoiceItem


def build_items(items_data):
    """Validate and build InvoiceItem objects from raw request data.

    Line totals and the running subtotal are always computed server-side —
    any client-supplied line_total/subtotal is ignored.
    """
    from app.utils.validation import parse_decimal
    from app.utils.errors import ApiError

    if not items_data or not isinstance(items_data, list):
        raise ApiError("At least one invoice item is required", 400)

    items = []
    for idx, raw in enumerate(items_data):
        if not isinstance(raw, dict) or not raw.get("name"):
            raise ApiError(f"Item {idx + 1} is missing a name", 400)

        quantity = parse_decimal(raw.get("quantity", 1), f"item[{idx}].quantity")
        if quantity <= 0:
            raise ApiError(f"Item {idx + 1} quantity must be greater than 0", 400)

        unit_price = parse_decimal(raw.get("unit_price"), f"item[{idx}].unit_price", min_value=0)

        item = InvoiceItem(
            name=str(raw["name"]).strip(),
            description=raw.get("description"),
            quantity=quantity,
            unit_price=unit_price,
        )
        item.compute_line_total()
        items.append(item)

    return items


def compute_totals(items, tax):
    subtotal = sum((item.line_total for item in items), Decimal("0.00"))
    subtotal = subtotal.quantize(Decimal("0.01"))
    tax = Decimal(tax).quantize(Decimal("0.01"))
    total = (subtotal + tax).quantize(Decimal("0.01"))
    return subtotal, tax, total
