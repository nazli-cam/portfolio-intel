"""Smoke tests — verify the app starts and core endpoints respond."""
import pytest
from fastapi.testclient import TestClient


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_login_wrong_credentials(client):
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_login_seeded_admin(client):
    r = client.post(
        "/auth/login",
        json={"email": "admin@portfoliointel.com", "password": "changeme123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"


def test_protected_route_without_token(client):
    r = client.get("/companies")
    assert r.status_code == 401


def test_protected_route_with_token(client):
    login = client.post(
        "/auth/login",
        json={"email": "admin@portfoliointel.com", "password": "changeme123"},
    )
    token = login.json()["access_token"]
    r = client.get("/companies", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_signal_count_endpoint(client):
    login = client.post(
        "/auth/login",
        json={"email": "admin@portfoliointel.com", "password": "changeme123"},
    )
    token = login.json()["access_token"]
    r = client.get("/signals/count", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "count" in r.json()
