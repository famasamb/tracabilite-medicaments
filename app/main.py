from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.db import engine
from app.core.migration import mettre_a_niveau
from app.api.auth import router as routeur_auth
from app.api.employes import router as routeur_employes
from app.api.lots import router as routeur_lots
from app.api.sr import router as routeur_sr
from app.api.tableau import router as routeur_tableau
from app.api.unites import router as routeur_unites
from app.api.produits import router as routeur_produits
from app.api.dispensations import router as routeur_dispensations
from app.api.evenements import router as routeur_evenements
from app.api.inscription import router as routeur_inscription
from app.api.conteneurs import router as routeur_conteneurs
from app.services.erreurs import ErreurMetier
from app.domaine import models  # noqa: F401  (charge les classes pour creer les tables)


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

@app.exception_handler(ErreurMetier)
async def erreur_metier(requete: Request, erreur: ErreurMetier):
    """Une regle metier refuse l'operation: meme reponse qu'une erreur HTTP classique."""
    return JSONResponse({"detail": erreur.detail}, status_code=erreur.status_code)


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
app.include_router(routeur_conteneurs)
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
