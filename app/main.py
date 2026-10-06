from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import Base, engine
from . import models  # noqa: F401  (charge les classes pour creer les tables)


@asynccontextmanager
async def demarrage(app: FastAPI):
    """Au demarrage de l'API, on cree les tables si elles n'existent pas encore."""
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Tracabilite des medicaments",
    description="Serialisation, tracabilite et detection d'anomalies, Senegal.",
    version="0.1.0",
    lifespan=demarrage,
)


@app.get("/sante", tags=["Systeme"])
def sante():
    """Verifie que l'API repond."""
    return {"etat": "ok"}