def test_register_success(client):
    resp = client.post("/api/auth/register", json={
        "name": "Alice", "email": "alice@example.com", "password": "supersecret1"
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["user"]["email"] == "alice@example.com"
    assert "password" not in data["user"]
    assert "access_token" in data


def test_register_duplicate_email(client, register):
    register(client)
    resp = client.post("/api/auth/register", json={
        "name": "Alice2", "email": "alice@example.com", "password": "supersecret1"
    })
    assert resp.status_code == 409


def test_register_missing_fields(client):
    resp = client.post("/api/auth/register", json={"email": "a@example.com"})
    assert resp.status_code == 400


def test_register_short_password(client):
    resp = client.post("/api/auth/register", json={
        "name": "Alice", "email": "alice@example.com", "password": "short"
    })
    assert resp.status_code == 400


def test_login_success(client, register):
    register(client)
    resp = client.post("/api/auth/login", json={
        "email": "alice@example.com", "password": "supersecret1"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_wrong_password(client, register):
    register(client)
    resp = client.post("/api/auth/login", json={
        "email": "alice@example.com", "password": "wrongpassword"
    })
    assert resp.status_code == 401


def test_me_requires_auth(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "alice@example.com"
