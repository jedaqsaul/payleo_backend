import datetime as dt


def test_customer_cross_user_update_forbidden(client, auth_headers, other_auth_headers):
    created = client.post("/api/customers/", headers=auth_headers, json={"name": "Acme"}).get_json()["customer"]
    resp = client.patch(f"/api/customers/{created['id']}/", headers=other_auth_headers, json={"name": "Hacked"})
    assert resp.status_code == 404


def test_customer_cross_user_delete_forbidden(client, auth_headers, other_auth_headers):
    created = client.post("/api/customers/", headers=auth_headers, json={"name": "Acme"}).get_json()["customer"]
    resp = client.delete(f"/api/customers/{created['id']}/", headers=other_auth_headers)
    assert resp.status_code == 404


def test_product_cross_user_update_forbidden(client, auth_headers, other_auth_headers):
    created = client.post("/api/products/", headers=auth_headers, json={
        "name": "Widget", "unit_price": "10.00"
    }).get_json()["product"]
    resp = client.patch(f"/api/products/{created['id']}/", headers=other_auth_headers, json={"unit_price": "0.01"})
    assert resp.status_code == 404


def test_invoice_cross_user_status_change_forbidden(client, auth_headers, other_auth_headers):
    customer = client.post("/api/customers/", headers=auth_headers, json={"name": "Acme"}).get_json()["customer"]
    issue = dt.date.today().isoformat()
    due = (dt.date.today() + dt.timedelta(days=10)).isoformat()
    invoice = client.post("/api/invoices/", headers=auth_headers, json={
        "customer_id": customer["id"], "issue_date": issue, "due_date": due,
        "items": [{"name": "Item", "quantity": 1, "unit_price": "5.00"}],
    }).get_json()["invoice"]

    resp = client.post(f"/api/invoices/{invoice['id']}/status/", headers=other_auth_headers, json={"status": "SENT"})
    assert resp.status_code == 404

    resp2 = client.get(f"/api/invoices/{invoice['id']}/pdf/", headers=other_auth_headers)
    assert resp2.status_code == 404

    resp3 = client.delete(f"/api/invoices/{invoice['id']}/", headers=other_auth_headers)
    assert resp3.status_code == 404


def test_invalid_json_body_handled(client, auth_headers):
    resp = client.post(
        "/api/customers/",
        headers={**auth_headers, "Content-Type": "application/json"},
        data="not-json",
    )
    assert resp.status_code == 400


def test_no_auth_header_rejected_everywhere(client):
    assert client.get("/api/customers/").status_code == 401
    assert client.get("/api/products/").status_code == 401
    assert client.get("/api/invoices/").status_code == 401
    assert client.get("/api/dashboard/summary/").status_code == 401


def test_malformed_token_rejected(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 422


def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
