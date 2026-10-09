from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from .db import engine
from .migration import mettre_a_niveau
from .routes_auth import router as routeur_auth
from .routes_employes import router as routeur_employes
from .routes_lots import router as routeur_lots
from .routes_sr import router as routeur_sr
from .routes_tableau import router as routeur_tableau
from .routes_unites import router as routeur_unites
from .routes_produits import router as routeur_produits
from .routes_dispensations import router as routeur_dispensations
from .routes_evenements import router as routeur_evenements
from .routes_inscription import router as routeur_inscription
from . import models  # noqa: F401  (charge les classes pour creer les tables)


@asynccontextmanager
async def demarrage(app: FastAPI):
    """Au demarrage de l'API, on cree les tables si elles n'existent pas encore."""
    mettre_a_niveau(engine)
    yield


app = FastAPI(
    title="Tracabilite des medicaments",
    description="Serialisation, tracabilite et detection d'anomalies, Senegal.",
    version="0.1.0",
    lifespan=demarrage,
)

# En-tetes de securite sur toutes les reponses. La politique de contenu (CSP) ne concerne que l'application
# mobile: elle n'accepte que des ressources de sa propre adresse. La camera et la position restent permises.
CSP_MOBILE = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
              "media-src 'self' blob:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; "
              "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")


@app.middleware("http")
async def en_tetes_securite(requete: Request, suite):
    reponse = await suite(requete)
    reponse.headers["X-Content-Type-Options"] = "nosniff"
    reponse.headers["X-Frame-Options"] = "DENY"
    reponse.headers["Referrer-Policy"] = "no-referrer"
    reponse.headers["Permissions-Policy"] = "camera=(self), geolocation=(self), microphone=()"
    if requete.url.path.startswith("/mobile"):
        reponse.headers["Content-Security-Policy"] = CSP_MOBILE
    return reponse


app.include_router(routeur_inscription)
app.include_router(routeur_auth)
app.include_router(routeur_employes)
app.include_router(routeur_produits)
app.include_router(routeur_lots)
app.include_router(routeur_evenements)
app.include_router(routeur_dispensations)
app.include_router(routeur_unites)
app.include_router(routeur_sr)
app.include_router(routeur_tableau)


# Application mobile (pages web servies par l'API, a la meme adresse)
app.mount("/mobile", StaticFiles(directory=Path(__file__).parent / "static" / "mobile", html=True), name="mobile")


@app.get("/sante", tags=["Systeme"])
def sante():
    """Verifie que l'API repond."""
    return {"etat": "ok"}
