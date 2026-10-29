def _create_customer(client, headers, name="Acme Corp", email="billing@acme.com"):
    return client.post("/api/customers/", headers=headers, json={
        "name": name, "email": email, "phone": "123-456", "address": "1 Main St"
    })


def test_create_customer(client, auth_headers):
    resp = _create_customer(client, auth_headers)
    assert resp.status_code == 201
    assert resp.get_json()["customer"]["name"] == "Acme Corp"


def test_create_customer_requires_name(client, auth_headers):
    resp = client.post("/api/customers/", headers=auth_headers, json={"email": "a@b.com"})
    assert resp.status_code == 400


def test_list_customers(client, auth_headers):
    _create_customer(client, auth_headers)
    _create_customer(client, auth_headers, name="Beta LLC", email="beta@example.com")
    resp = client.get("/api/customers/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["customers"]) == 2
    assert data["pagination"]["total"] == 2


def test_get_customer_ownership(client, auth_headers, other_auth_headers):
    created = _create_customer(client, auth_headers).get_json()["customer"]
    resp = client.get(f"/api/customers/{created['id']}/", headers=other_auth_headers)
    assert resp.status_code == 404


def test_update_customer(client, auth_headers):
    created = _create_customer(client, auth_headers).get_json()["customer"]
    resp = client.patch(f"/api/customers/{created['id']}/", headers=auth_headers, json={"name": "Acme Corp Updated"})
    assert resp.status_code == 200
    assert resp.get_json()["customer"]["name"] == "Acme Corp Updated"


def test_delete_customer(client, auth_headers):
    created = _create_customer(client, auth_headers).get_json()["customer"]
    resp = client.delete(f"/api/customers/{created['id']}/", headers=auth_headers)
    assert resp.status_code == 200
    resp2 = client.get(f"/api/customers/{created['id']}/", headers=auth_headers)
    assert resp2.status_code == 404


def test_search_customers_by_name(client, auth_headers):
    _create_customer(client, auth_headers, name="Acme Corp", email="a@acme.com")
    _create_customer(client, auth_headers, name="Zeta Inc", email="z@zeta.com")
    resp = client.get("/api/customers/?search=Acme", headers=auth_headers)
    data = resp.get_json()
    assert len(data["customers"]) == 1
    assert data["customers"][0]["name"] == "Acme Corp"


def test_customers_require_auth(client):
    resp = client.get("/api/customers/")
    assert resp.status_code == 401
