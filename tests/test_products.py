def _create_product(client, headers, name="Consulting Hour", price="75.00"):
    return client.post("/api/products/", headers=headers, json={
        "name": name, "description": "General consulting", "unit_price": price
    })


def test_create_product(client, auth_headers):
    resp = _create_product(client, auth_headers)
    assert resp.status_code == 201
    assert resp.get_json()["product"]["unit_price"] == "75.00"


def test_create_product_negative_price_rejected(client, auth_headers):
    resp = _create_product(client, auth_headers, price="-5.00")
    assert resp.status_code == 400


def test_create_product_missing_price(client, auth_headers):
    resp = client.post("/api/products/", headers=auth_headers, json={"name": "X"})
    assert resp.status_code == 400


def test_list_products_ownership(client, auth_headers, other_auth_headers):
    _create_product(client, auth_headers)
    resp = client.get("/api/products/", headers=other_auth_headers)
    assert resp.get_json()["pagination"]["total"] == 0


def test_update_product(client, auth_headers):
    created = _create_product(client, auth_headers).get_json()["product"]
    resp = client.put(f"/api/products/{created['id']}/", headers=auth_headers, json={"unit_price": "99.99"})
    assert resp.status_code == 200
    assert resp.get_json()["product"]["unit_price"] == "99.99"


def test_delete_product(client, auth_headers):
    created = _create_product(client, auth_headers).get_json()["product"]
    resp = client.delete(f"/api/products/{created['id']}/", headers=auth_headers)
    assert resp.status_code == 200
