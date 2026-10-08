import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app as application
from app.references import charger_references


def _moteur_en_memoire():
    return create_engine("sqlite://", connect_args={"check_same_thread": False},
                         poolclass=StaticPool)


@pytest.fixture(autouse=True)
def courriels(monkeypatch):
    """Aucun courriel n'est envoye pendant les tests: ils sont ranges dans cette liste."""
    envoyes = []
    monkeypatch.setattr("app.courriel.envoyer", lambda destinataire, sujet, texte: envoyes.append(
        {"a": destinataire, "sujet": sujet, "texte": texte}))
    return envoyes


@pytest.fixture
def db():
    """Une base SQLite en memoire, toute neuve pour chaque test."""
    moteur = _moteur_en_memoire()
    Base.metadata.create_all(moteur)
    with Session(moteur) as session:
        yield session
    moteur.dispose()


@pytest.fixture
def client():
    """Un client de test de l'API, branche sur une base en memoire contenant les references de test."""
    moteur = _moteur_en_memoire()
    Base.metadata.create_all(moteur)
    with Session(moteur) as session:
        charger_references(session, "data/references_test.csv")

    def base_de_test():
        with Session(moteur) as session:
            yield session

    application.dependency_overrides[get_db] = base_de_test
    with TestClient(application) as c:
        yield c
    application.dependency_overrides.clear()
    moteur.dispose()
