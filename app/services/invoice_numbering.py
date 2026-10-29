from flask import current_app

from app.models.invoice import Invoice


def generate_invoice_number(user_id):
    """Generate the next sequential invoice number for a user, e.g. INV-000001.

    Uses a count-based approach guarded by the unique (user_id, invoice_number)
    constraint at the database level, so a collision under concurrency raises
    an IntegrityError rather than silently duplicating a number.
    """
    prefix = current_app.config.get("INVOICE_NUMBER_PREFIX", "INV-")
    padding = current_app.config.get("INVOICE_NUMBER_PADDING", 6)

    count = Invoice.query.filter_by(user_id=user_id).count()
    next_seq = count + 1

    while True:
        candidate = f"{prefix}{str(next_seq).zfill(padding)}"
        exists = Invoice.query.filter_by(user_id=user_id, invoice_number=candidate).first()
        if not exists:
            return candidate
        next_seq += 1
