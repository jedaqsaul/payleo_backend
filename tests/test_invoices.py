import datetime as dt

import pytest


def _create_customer(client, headers, name="Acme Corp"):
    return client.post("/api/customers/", headers=headers, json={
        "name": name, "email": "billing@acme.com"
    }).get_json()["customer"]


def _dates(days_until_due=30):
    issue = dt.date.today().isoformat()
    due = (dt.date.today() + dt.timedelta(days=days_until_due)).isoformat()
    return issue, due


def _create_invoice(client, headers, customer_id=None, items=None, tax="10.00", days_until_due=30):
    if items is None:
        items = [
            {"name": "Design work", "quantity": 2, "unit_price": "50.00"},
            {"name": "Hosting", "quantity": 1, "unit_price": "20.00"},
        ]
    issue, due = _dates(days_until_due)
    return client.post("/api/invoices/", headers=headers, json={
        "customer_id": customer_id,
        "issue_date": issue,
        "due_date": due,
        "items": items,
        "tax": tax,
        "notes": "Thanks for your business",
    })


@pytest.fixture()
def customer(client, auth_headers):
    return _create_customer(client, auth_headers)


def test_create_invoice_calculates_totals(client, auth_headers, customer):
    resp = _create_invoice(client, auth_headers, customer_id=customer["id"])
    assert resp.status_code == 201
    invoice = resp.get_json()["invoice"]
    # subtotal = 2*50 + 1*20 = 120; tax=10; total=130
    assert invoice["subtotal"] == "120.00"
    assert invoice["tax"] == "10.00"
    assert invoice["total"] == "130.00"
    assert invoice["status"] == "DRAFT"
    assert invoice["invoice_number"].startswith("INV-")
    assert len(invoice["items"]) == 2
    assert invoice["items"][0]["line_total"] == "100.00"


def test_create_invoice_ignores_client_supplied_totals(client, auth_headers, customer):
    issue, due = _dates()
    resp = client.post("/api/invoices/", headers=auth_headers, json={
        "customer_id": customer["id"],
        "issue_date": issue,
        "due_date": due,
        "items": [{"name": "Item", "quantity": 1, "unit_price": "10.00", "line_total": "999999.99"}],
        "tax": "0.00",
        "subtotal": "999999.99",
        "total": "999999.99",
    })
    invoice = resp.get_json()["invoice"]
    assert invoice["subtotal"] == "10.00"
    assert invoice["total"] == "10.00"


def test_invoice_numbers_sequential_and_unique(client, auth_headers, customer):
    r1 = _create_invoice(client, auth_headers, customer_id=customer["id"])
    r2 = _create_invoice(client, auth_headers, customer_id=customer["id"])
    n1 = r1.get_json()["invoice"]["invoice_number"]
    n2 = r2.get_json()["invoice"]["invoice_number"]
    assert n1 != n2


def test_create_invoice_requires_items(client, auth_headers, customer):
    issue, due = _dates()
    resp = client.post("/api/invoices/", headers=auth_headers, json={
        "customer_id": customer["id"], "issue_date": issue, "due_date": due, "items": []
    })
    assert resp.status_code == 400


def test_create_invoice_invalid_quantity(client, auth_headers, customer):
    resp = _create_invoice(client, auth_headers, customer_id=customer["id"], items=[
        {"name": "Bad item", "quantity": 0, "unit_price": "10.00"}
    ])
    assert resp.status_code == 400


def test_create_invoice_invalid_price(client, auth_headers, customer):
    resp = _create_invoice(client, auth_headers, customer_id=customer["id"], items=[
        {"name": "Bad item", "quantity": 1, "unit_price": "-10.00"}
    ])
    assert resp.status_code == 400


def test_create_invoice_due_before_issue_rejected(client, auth_headers, customer):
    resp = _create_invoice(client, auth_headers, customer_id=customer["id"], days_until_due=-5)
    assert resp.status_code == 400


def test_create_invoice_other_users_customer_rejected(client, auth_headers, other_auth_headers, customer):
    resp = _create_invoice(client, other_auth_headers, customer_id=customer["id"])
    assert resp.status_code == 400


def test_unauthorized_invoice_access(client, auth_headers, other_auth_headers, customer):
    created = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    resp = client.get(f"/api/invoices/{created['id']}/", headers=other_auth_headers)
    assert resp.status_code == 404


def test_status_transitions_valid(client, auth_headers, customer):
    invoice = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    resp = client.post(f"/api/invoices/{invoice['id']}/status/", headers=auth_headers, json={"status": "SENT"})
    assert resp.status_code == 200
    assert resp.get_json()["invoice"]["status"] == "SENT"


def test_status_transitions_invalid(client, auth_headers, customer):
    invoice = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    # DRAFT -> PAID is not allowed directly
    resp = client.post(f"/api/invoices/{invoice['id']}/status/", headers=auth_headers, json={"status": "PAID"})
    assert resp.status_code == 409


def test_cancelled_invoice_cannot_become_paid(client, auth_headers, customer):
    invoice = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    client.post(f"/api/invoices/{invoice['id']}/status/", headers=auth_headers, json={"status": "CANCELLED"})
    resp = client.post(f"/api/invoices/{invoice['id']}/mark-paid/", headers=auth_headers)
    assert resp.status_code == 409


def test_mark_paid_flow(client, auth_headers, customer):
    invoice = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    client.post(f"/api/invoices/{invoice['id']}/status/", headers=auth_headers, json={"status": "SENT"})
    resp = client.post(f"/api/invoices/{invoice['id']}/mark-paid/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()["invoice"]
    assert data["status"] == "PAID"
    assert data["paid_at"] is not None


def test_overdue_detection(client, auth_headers, customer):
    invoice = _create_invoice(client, auth_headers, customer_id=customer["id"], days_until_due=1).get_json()["invoice"]
    client.post(f"/api/invoices/{invoice['id']}/status/", headers=auth_headers, json={"status": "SENT"})
    # Manually push the due date into the past to simulate overdue.
    from app.models.invoice import Invoice
    from app.extensions import db
    inv = Invoice.query.get(invoice["id"])
    inv.due_date = inv.due_date - __import__("datetime").timedelta(days=10)
    db.session.commit()

    resp = client.get(f"/api/invoices/{invoice['id']}/", headers=auth_headers)
    assert resp.get_json()["invoice"]["status"] == "OVERDUE"


def test_pdf_generation(client, auth_headers, customer):
    invoice = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    resp = client.get(f"/api/invoices/{invoice['id']}/pdf/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"
    assert resp.data[:4] == b"%PDF"


def test_pdf_unauthorized_access(client, auth_headers, other_auth_headers, customer):
    invoice = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    resp = client.get(f"/api/invoices/{invoice['id']}/pdf/", headers=other_auth_headers)
    assert resp.status_code == 404


def test_filter_by_status(client, auth_headers, customer):
    inv1 = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    _create_invoice(client, auth_headers, customer_id=customer["id"])
    client.post(f"/api/invoices/{inv1['id']}/status/", headers=auth_headers, json={"status": "SENT"})

    resp = client.get("/api/invoices/?status=SENT", headers=auth_headers)
    data = resp.get_json()
    assert data["pagination"]["total"] == 1
    assert data["invoices"][0]["id"] == inv1["id"]


def test_filter_by_customer(client, auth_headers, customer):
    other_customer = _create_customer(client, auth_headers, name="Other Co")
    _create_invoice(client, auth_headers, customer_id=customer["id"])
    _create_invoice(client, auth_headers, customer_id=other_customer["id"])

    resp = client.get(f"/api/invoices/?customer_id={customer['id']}", headers=auth_headers)
    assert resp.get_json()["pagination"]["total"] == 1


def test_search_by_invoice_number(client, auth_headers, customer):
    invoice = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    resp = client.get(f"/api/invoices/?search={invoice['invoice_number']}", headers=auth_headers)
    assert resp.get_json()["pagination"]["total"] == 1


def test_pagination(client, auth_headers, customer):
    for _ in range(5):
        _create_invoice(client, auth_headers, customer_id=customer["id"])
    resp = client.get("/api/invoices/?page=1&per_page=2", headers=auth_headers)
    data = resp.get_json()
    assert len(data["invoices"]) == 2
    assert data["pagination"]["total"] == 5
    assert data["pagination"]["pages"] == 3


def test_delete_paid_invoice_forbidden(client, auth_headers, customer):
    invoice = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    client.post(f"/api/invoices/{invoice['id']}/status/", headers=auth_headers, json={"status": "SENT"})
    client.post(f"/api/invoices/{invoice['id']}/mark-paid/", headers=auth_headers)
    resp = client.delete(f"/api/invoices/{invoice['id']}/", headers=auth_headers)
    assert resp.status_code == 409


def test_dashboard_summary(client, auth_headers, customer):
    inv1 = _create_invoice(client, auth_headers, customer_id=customer["id"]).get_json()["invoice"]
    _create_invoice(client, auth_headers, customer_id=customer["id"])
    client.post(f"/api/invoices/{inv1['id']}/status/", headers=auth_headers, json={"status": "SENT"})
    client.post(f"/api/invoices/{inv1['id']}/mark-paid/", headers=auth_headers)

    resp = client.get("/api/dashboard/summary/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_invoices"] == 2
    assert data["paid_invoices"] == 1
    assert data["total_paid"] == "130.00"
