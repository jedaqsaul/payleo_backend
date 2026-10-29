import pytest

from app import create_app
from app.extensions import db as _db
from config import TestingConfig


@pytest.fixture()
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _register(client, email="alice@example.com", password="supersecret1", name="Alice"):
    return client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )


@pytest.fixture()
def auth_headers(client):
    resp = _register(client)
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def other_auth_headers(client):
    resp = _register(client, email="bob@example.com", name="Bob")
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def register():
    return _register
