import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
import app.models  # noqa: F401  (charge les classes pour creer les tables)


@pytest.fixture
def db():
    """Une base SQLite en memoire, toute neuve pour chaque test."""
    moteur = create_engine("sqlite://")
    Base.metadata.create_all(moteur)
    with Session(moteur) as session:
        yield session
    moteur.dispose()