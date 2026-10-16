"""Agregation: composer un carton ou une palette, consulter son contenu, imprimer son etiquette."""
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response as ReponseHttp, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .agregation import (composer, enregistrer_pour_conteneur, extraire_sscc, numeros_de_serie_contenus,
                         ouvrir)
from .auth import fabricant_courant, utilisateur_courant
from .codes import generer_image_code
from .db import get_db
from .horsligne import verifier_identifiant_client
from .lecture import lire_hybride
from .models import Conteneur, NiveauConteneur, TypeOperation, TypeStructure, Utilisateur
from .routes_evenements import OPERATIONS_AUTORISEES, TAILLE_MAX_IMAGE
from .schemas import (ConteneurEntree, ConteneurEvenementSortie, ConteneurSortie, OuvertureEntree,
                      OuvertureSortie)

router = APIRouter(prefix="/conteneurs", tags=["Conteneurs (agregation)"])

STRUCTURES_AUTORISEES = {TypeStructure.fabricant, TypeStructure.grossisteRepartiteur,
                         TypeStructure.SR, TypeStructure.officine}


def _sortie(db: Session, conteneur: Conteneur, message: str = "", utilisateur: Utilisateur | None = None) -> ConteneurSortie:
    directs = [l.enfant_unite or l.enfant_conteneur for l in conteneur.contenu if l.dateRetrait is None]
    return ConteneurSortie(sscc=conteneur.sscc, niveau=conteneur.niveau, etat=conteneur.etat,
                           structure=conteneur.structure.nom, dateCreation=conteneur.dateCreation,
                           elements=directs, nombreBoites=len(numeros_de_serie_contenus(db, conteneur)),
                           chezVous=utilisateur is not None and conteneur.structure_id == utilisateur.structure_id,
                           message=message)


@router.post("", response_model=ConteneurSortie, status_code=201)
def composer_un_conteneur(donnees: ConteneurEntree,
                          utilisateur: Utilisateur = Depends(fabricant_courant),
                          db: Session = Depends(get_db)):
    """Cree un carton (a partir des numeros de serie de ses boites) ou une palette (a partir des SSCC de ses cartons)."""
    conteneur = composer(db, utilisateur, donnees.niveau, donnees.elements)
    nom = "Carton" if conteneur.niveau == NiveauConteneur.carton else "Palette"
    return _sortie(db, conteneur, f"{nom} {conteneur.sscc} cree.", utilisateur)


async def obtenir_conteneur(db: Session, image: UploadFile | None, sscc: str | None) -> Conteneur:
    """Lit le code du carton ou de la palette sur l'image; si elle echoue, utilise le SSCC saisi."""
    saisie = sscc.strip() if sscc else None
    identifiant = None
    methode = None
    if image is not None:
        contenu = await image.read(TAILLE_MAX_IMAGE + 1)
        if len(contenu) > TAILLE_MAX_IMAGE:
            raise HTTPException(413, "Image trop volumineuse (5 Mo maximum).")
        lecture = await run_in_threadpool(lire_hybride, contenu)
        identifiant = extraire_sscc(lecture.texte) if lecture.texte else None
        methode = lecture.methode if identifiant else None
    if identifiant is None:
        identifiant = saisie
        methode = "saisie" if saisie else None
    if identifiant is None:
        if image is None:
            raise HTTPException(422, "Envoyez l'image du code ou saisissez le SSCC.")
        raise HTTPException(422, "Code illisible. Reprenez la photo ou saisissez le SSCC.")
    conteneur = db.get(Conteneur, identifiant)
    if conteneur is None:
        raise HTTPException(404, "Conteneur inconnu: aucun carton ni palette avec ce SSCC.")
    conteneur.methode_lecture = methode   # information de la requete en cours, non enregistree en base
    return conteneur


@router.post("/evenements", response_model=ConteneurEvenementSortie, status_code=201)
async def enregistrer_pour_un_conteneur(
        typeOperation: TypeOperation = Form(description="reception ou expedition"),
        image: UploadFile | None = File(default=None, description="Photo du code DataMatrix du carton ou de la palette"),
        sscc: str | None = Form(default=None, description="Saisie manuelle si le code est illisible"),
        latitude: float | None = Form(default=None, ge=-90, le=90),
        longitude: float | None = Form(default=None, ge=-180, le=180),
        dateHeure: datetime | None = Form(default=None, description="Date reelle de l'operation (sans reseau)"),
        identifiantClient: str | None = Form(default=None, description="Identifiant fabrique par le telephone"),
        reponse: ReponseHttp = None,
        utilisateur: Utilisateur = Depends(utilisateur_courant),
        db: Session = Depends(get_db)):
    """Reception ou expedition d'un carton ou d'une palette: un seul scan enregistre toutes les boites contenues."""
    if typeOperation not in (TypeOperation.reception, TypeOperation.expedition):
        raise HTTPException(422, "Operation non geree ici: reception ou expedition seulement.")
    if typeOperation not in OPERATIONS_AUTORISEES.get(utilisateur.structure.type, set()):
        raise HTTPException(403, "Votre structure n'est pas autorisee a enregistrer cette operation.")
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "Fournissez la latitude et la longitude ensemble, ou aucune des deux.")
    identifiantClient = verifier_identifiant_client(identifiantClient)

    conteneur = await obtenir_conteneur(db, image, sscc)
    boites, alertes, deja, date_operation = enregistrer_pour_conteneur(
        db, utilisateur, conteneur, typeOperation, latitude, longitude, dateHeure, identifiantClient)
    if deja:
        reponse.status_code = 200
    nom = "Carton" if conteneur.niveau == NiveauConteneur.carton else "Palette"
    message = f"{nom} enregistre: {boites} boite(s)."
    if alertes:
        message += f" {alertes} alerte(s) a verifier."
    return ConteneurEvenementSortie(sscc=conteneur.sscc, niveau=conteneur.niveau, typeOperation=typeOperation,
                                    dateHeure=date_operation, latitude=latitude, longitude=longitude,
                                    nombreBoites=boites, nombreAlertes=alertes, alerte=alertes > 0, message=message,
                                    methodeLecture=getattr(conteneur, "methode_lecture", None))


@router.post("/{sscc}/ouvrir", response_model=OuvertureSortie)
def ouvrir_un_conteneur(sscc: str, donnees: OuvertureEntree | None = None,
                        utilisateur: Utilisateur = Depends(utilisateur_courant),
                        db: Session = Depends(get_db)):
    """Ouvre un carton (ses boites redeviennent des unites seules) ou une palette (ses cartons redeviennent seuls).

    Seule la structure qui detient le conteneur peut l'ouvrir. Si la liste de ce qui a ete trouve est fournie,
    ce qui manque est signale par une alerte "carton incomplet"."""
    conteneur = db.get(Conteneur, sscc)
    if conteneur is None:
        raise HTTPException(404, "Conteneur inconnu.")
    liberes, manquants, alertes = ouvrir(db, utilisateur, conteneur, donnees.presentes if donnees else None)
    nom = "Carton" if conteneur.niveau == NiveauConteneur.carton else "Palette"
    message = f"{nom} ouvert: {len(liberes)} element(s) libere(s)."
    if manquants:
        message += f" {len(manquants)} manquant(s), {alertes} alerte(s) a verifier."
    return OuvertureSortie(sscc=conteneur.sscc, niveau=conteneur.niveau, elementsLiberes=len(liberes),
                           manquants=manquants, nombreAlertes=alertes, alerte=bool(manquants), message=message)


@router.post("/lecture", response_model=ConteneurSortie)
async def lire_un_conteneur(
        image: UploadFile | None = File(default=None, description="Photo du code DataMatrix du carton ou de la palette"),
        sscc: str | None = Form(default=None, description="Saisie manuelle si le code est illisible"),
        utilisateur: Utilisateur = Depends(utilisateur_courant),
        db: Session = Depends(get_db)):
    """Lit l'etiquette d'un carton ou d'une palette (ou prend le SSCC saisi) et renvoie son contenu actuel."""
    if utilisateur.structure.type not in STRUCTURES_AUTORISEES:
        raise HTTPException(403, "Votre structure n'est pas autorisee a consulter un conteneur.")
    conteneur = await obtenir_conteneur(db, image, sscc)
    sortie = _sortie(db, conteneur, utilisateur=utilisateur)
    sortie.methodeLecture = getattr(conteneur, "methode_lecture", None)
    return sortie


@router.get("/{sscc}", response_model=ConteneurSortie)
def consulter_un_conteneur(sscc: str,
                           utilisateur: Utilisateur = Depends(utilisateur_courant),
                           db: Session = Depends(get_db)):
    """Contenu actuel d'un carton ou d'une palette."""
    if utilisateur.structure.type not in STRUCTURES_AUTORISEES:
        raise HTTPException(403, "Votre structure n'est pas autorisee a consulter un conteneur.")
    conteneur = db.get(Conteneur, sscc)
    if conteneur is None:
        raise HTTPException(404, "Conteneur inconnu.")
    return _sortie(db, conteneur, utilisateur=utilisateur)


@router.get("/{sscc}/etiquette", response_class=Response,
            responses={200: {"content": {"image/png": {}}, "description": "Etiquette DataMatrix du conteneur"}})
def etiquette_du_conteneur(sscc: str,
                           utilisateur: Utilisateur = Depends(fabricant_courant),
                           db: Session = Depends(get_db)):
    """Image de l'etiquette a imprimer: code DataMatrix GS1 portant le SSCC, avec le texte lisible dessous."""
    conteneur = db.get(Conteneur, sscc)
    if conteneur is None or conteneur.structure_id != utilisateur.structure_id:
        raise HTTPException(404, "Conteneur inconnu.")
    return Response(content=generer_image_code(f"(00){conteneur.sscc}", avec_texte=True), media_type="image/png")
