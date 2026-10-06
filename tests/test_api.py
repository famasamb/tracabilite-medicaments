"""Tests de l'API."""
from fastapi.testclient import TestClient

from app.main import app


def test_sante():
    with TestClient(app) as client:
        reponse = client.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json() == {"etat": "ok"}