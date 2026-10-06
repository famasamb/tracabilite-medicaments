from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import Base, engine
from .routes_inscription import router as routeur_inscription
from .routes_auth import router as routeur_auth
from .routes_employes import router as routeur_employes
from .routes_produits import router as routeur_produits
from .routes_lots import router as routeur_lots
from .routes_evenements import router as routeur_evenements
from .routes_dispensations import router as routeur_dispensations
from .routes_unites import router as routeur_unites
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

app.include_router(routeur_inscription)
app.include_router(routeur_auth)
app.include_router(routeur_employes)
app.include_router(routeur_produits)
app.include_router(routeur_lots)
app.include_router(routeur_evenements)
app.include_router(routeur_dispensations)
app.include_router(routeur_unites)


@app.get("/sante", tags=["Systeme"])
def sante():
    """Verifie que l'API repond."""
    return {"etat": "ok"}