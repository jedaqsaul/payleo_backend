import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, date

from app.utils.errors import ApiError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def require_fields(data, fields):
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    missing = [f for f in fields if data.get(f) in (None, "")]
    if missing:
        raise ApiError("Missing required field(s)", 400, {"missing": missing})


def validate_email(email, required=True):
    if email in (None, ""):
        if required:
            raise ApiError("Email is required", 400)
        return None
    if not EMAIL_RE.match(email):
        raise ApiError("Invalid email format", 400)
    return email.strip().lower()


def parse_decimal(value, field_name="value", min_value=None, allow_none=False):
    if value is None:
        if allow_none:
            return None
        raise ApiError(f"{field_name} is required", 400)
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ApiError(f"{field_name} must be a valid number", 400)
    if min_value is not None and dec < Decimal(str(min_value)):
        raise ApiError(f"{field_name} must be >= {min_value}", 400)
    return dec


def parse_date(value, field_name="date"):
    if value is None:
        raise ApiError(f"{field_name} is required", 400)
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ApiError(f"{field_name} must be in YYYY-MM-DD format", 400)
