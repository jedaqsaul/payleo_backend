"""Seed PayLeo with a ready-to-explore demo account.

Usage:
    python seed.py                 # create the demo account (skips if it already exists)
    python seed.py --reset         # delete the demo account and recreate it fresh
    python seed.py --email me@example.com --password 'MyPass123'

Dates are relative to today, so the data always looks current. All totals,
invoice numbers and statuses go through the same services the API uses.
"""
import argparse
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import inspect  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Customer, Invoice, InvoiceStatus, Product, User  # noqa: E402
from app.services.invoice_calculator import build_items, compute_totals  # noqa: E402
from app.services.invoice_numbering import generate_invoice_number  # noqa: E402

DEMO_NAME = "Demo Studio"
DEMO_EMAIL = "demo@payleo.app"
DEMO_PASSWORD = "DemoPass123"

CUSTOMERS = [
    ("Brightpath Labs", "accounts@brightpath.example", "+1 555 0101", "12 Market Street\nSpringfield"),
    ("Harbor & Finch Cafe", "owner@harborfinch.example", "+1 555 0102", "4 Dockside Road\nPort Haven"),
    ("Meridian Clinic", "billing@meridian.example", "+1 555 0103", "88 Parkview Avenue\nRiverton"),
    ("Oakline Furniture", "finance@oakline.example", "+1 555 0104", "230 Mill Lane\nGreenfield"),
    ("Studio Nine", "hello@studionine.example", "+1 555 0105", "9 Canal Walk\nBrookside"),
    ("Tembo Logistics", "ap@tembo.example", "+1 555 0106", "Unit 5, Freight Park\nEastgate"),
]

PRODUCTS = [
    ("Brand identity package", "Logo, colour palette, typography and brand guide", "2400.00"),
    ("Website design (per page)", "Responsive page design with one revision round", "450.00"),
    ("Monthly retainer", "Ongoing design and support, up to 10 hours", "800.00"),
    ("Consulting hour", "Strategy and advisory time", "95.00"),
    ("Logo design", "Three concepts, two revision rounds", "600.00"),
    ("Photography half day", "On-site shoot with edited selects", "350.00"),
    ("Copywriting (per 500 words)", "Web or marketing copy", "60.00"),
    ("Hosting and maintenance", "Monthly hosting, updates and backups", "40.00"),
]

# (customer, issued days ago, due offset from today, status, paid days ago, [(product, qty)], tax %, notes)
INVOICES = [
    (0, 75, -61, "PAID", 58, [(0, 1), (7, 1)], 10, "Thank you for your business."),
    (1, 62, -48, "PAID", 50, [(4, 1), (6, 4)], 0, None),
    (2, 45, -31, "PAID", 33, [(2, 1), (3, 3)], 10, "Payment by bank transfer."),
    (3, 30, -16, "PAID", 18, [(1, 3), (7, 1)], 0, None),
    (4, 40, -12, "OVERDUE", None, [(5, 1), (6, 6)], 0, "Reminder sent. Please settle at your earliest convenience."),
    (5, 28, -6, "OVERDUE", None, [(2, 1)], 10, None),
    (0, 10, 4, "SENT", None, [(1, 2), (3, 2)], 10, None),
    (2, 6, 8, "SENT", None, [(2, 1), (7, 1)], 0, "Payment due within 14 days."),
    (3, 3, 11, "SENT", None, [(0, 1)], 10, None),
    (1, 1, 13, "DRAFT", None, [(6, 3), (3, 1)], 0, None),
    (4, 0, 14, "DRAFT", None, [(4, 1), (1, 2)], 10, "Draft pending client sign-off."),
    (5, 35, -21, "CANCELLED", None, [(5, 2)], 0, "Cancelled: shoot postponed."),
]


def _at(days_ago, hour=9):
    d = date.today() - timedelta(days=days_ago)
    return datetime.combine(d, time(hour, 0), tzinfo=timezone.utc)


def seed(email, password, name, reset):
    existing = User.query.filter_by(email=email).first()
    if existing and not reset:
        print(f"Demo account {email} already exists. Use --reset to recreate it.")
        return False
    if existing:
        db.session.delete(existing)
        db.session.commit()
        print(f"Removed existing account {email}")

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    customers = []
    for cname, cemail, phone, address in CUSTOMERS:
        c = Customer(user_id=user.id, name=cname, email=cemail, phone=phone, address=address)
        db.session.add(c)
        customers.append(c)
    products = []
    for pname, desc, price in PRODUCTS:
        p = Product(user_id=user.id, name=pname, description=desc, unit_price=Decimal(price))
        db.session.add(p)
        products.append(p)
    db.session.flush()

    # Oldest first so invoice numbers ascend chronologically.
    for cust_i, issued_ago, due_offset, status, paid_ago, lines, tax_pct, notes in sorted(INVOICES, key=lambda r: -r[1]):
        items = build_items([
            {"name": products[pi].name, "description": products[pi].description,
             "quantity": qty, "unit_price": str(products[pi].unit_price)}
            for pi, qty in lines
        ])
        subtotal = sum((i.line_total for i in items), Decimal("0.00"))
        tax = (subtotal * Decimal(tax_pct) / Decimal(100)).quantize(Decimal("0.01"))
        subtotal, tax, total = compute_totals(items, tax)

        invoice = Invoice(
            user_id=user.id,
            customer_id=customers[cust_i].id,
            invoice_number=generate_invoice_number(user.id),
            issue_date=date.today() - timedelta(days=issued_ago),
            due_date=date.today() + timedelta(days=due_offset),
            status=InvoiceStatus[status],
            subtotal=subtotal, tax=tax, total=total,
            notes=notes,
            paid_at=_at(paid_ago, 14) if paid_ago is not None else None,
            created_at=_at(issued_ago),
        )
        invoice.items = items
        db.session.add(invoice)
        db.session.flush()

    db.session.commit()
    print(f"Seeded {len(CUSTOMERS)} customers, {len(PRODUCTS)} products, {len(INVOICES)} invoices.")
    print(f"\n  Sign in with:\n    email:    {email}\n    password: {password}\n")
    return True


def main():
    parser = argparse.ArgumentParser(description="Seed PayLeo with demo data.")
    parser.add_argument("--reset", action="store_true", help="delete the demo account first, then recreate it")
    parser.add_argument("--email", default=DEMO_EMAIL)
    parser.add_argument("--password", default=DEMO_PASSWORD)
    parser.add_argument("--name", default=DEMO_NAME)
    parser.add_argument("--force", action="store_true", help="allow seeding when FLASK_ENV=production")
    args = parser.parse_args()

    if os.environ.get("FLASK_ENV") == "production" and not args.force:
        sys.exit("Refusing to seed with FLASK_ENV=production (demo credentials are public). Use --force to override.")
    if len(args.password) < 8:
        sys.exit("Password must be at least 8 characters.")

    app = create_app()
    with app.app_context():
        if not inspect(db.engine).has_table("users"):
            sys.exit("Database tables are missing. Run `flask db upgrade` first.")
        seed(args.email.strip().lower(), args.password, args.name, args.reset)


if __name__ == "__main__":
    main()
