"""Cas d'utilisation Enregistrer la reception / Enregistrer l'expedition (fiche 7)."""
import logging
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .auth import utilisateur_courant
from .lecture import lire_hybride
from .db import get_db
from .models import (Anomalie, Evenement, StatutUnite, TypeAnomalie, TypeOperation,
                     TypeStructure, Unite, Utilisateur)
from .schemas import EvenementSortie

journal = logging.getLogger("tracabilite.lecture")
router = APIRouter(prefix="/evenements", tags=["Evenements"])

TAILLE_MAX_IMAGE = 5 * 1024 * 1024  # 5 Mo

# Qui peut faire quoi (acteurs de la fiche 7)
OPERATIONS_AUTORISEES = {
    TypeStructure.fabricant: {TypeOperation.expedition},
    TypeStructure.grossisteRepartiteur: {TypeOperation.reception, TypeOperation.expedition},
    TypeStructure.SR: {TypeOperation.reception, TypeOperation.expedition},
    TypeStructure.officine: {TypeOperation.reception},
}


def extraire_numero_serie(texte: str) -> str | None:
    """Dans le texte d'un code GS1, ex. (01)...(17)...(10)...(21)ABC123, renvoie la valeur de (21)."""
    trouve = re.search(r"\(21\)([^()]+)", texte)
    return trouve.group(1) if trouve else None


async def obtenir_unite(db: Session, image: UploadFile | None, numero_serie: str | None) -> Unite:
    """Lit le code sur l'image (methode classique); si elle echoue, utilise la saisie manuelle.

    Renvoie l'unite trouvee dans la base centrale, ou refuse la requete avec un message clair.
    """
    saisie = numero_serie.strip() if numero_serie else None
    identifiant = None
    methode = None
    if image is not None:
        contenu = await image.read(TAILLE_MAX_IMAGE + 1)
        if len(contenu) > TAILLE_MAX_IMAGE:
            raise HTTPException(413, "Image trop volumineuse (5 Mo maximum).")
        lecture = await run_in_threadpool(lire_hybride, contenu)   # classique, puis deep learning si besoin
        identifiant = extraire_numero_serie(lecture.texte) if lecture.texte else None
        methode = lecture.methode if identifiant else None
        journal.info("Lecture du code: %s", methode or "echec")
    if identifiant is None:
        identifiant = saisie
        methode = "saisie" if saisie else None
    if identifiant is None:
        if image is None:
            raise HTTPException(422, "Envoyez l'image du code ou saisissez le numero de serie.")
        raise HTTPException(422, "Code illisible. Reprenez la photo ou saisissez le numero de serie.")

    unite = db.get(Unite, identifiant)
    if unite is None:
        raise HTTPException(404, "Identifiant inconnu: aucune unite serialisee avec ce numero.")
    unite.methode_lecture = methode   # information de la requete en cours, non enregistree en base
    return unite


@router.post("", response_model=EvenementSortie, status_code=201)
async def enregistrer_evenement(
        typeOperation: TypeOperation = Form(description="reception ou expedition"),
        image: UploadFile | None = File(default=None, description="Photo du code DataMatrix"),
        numeroSerie: str | None = Form(default=None, description="Saisie manuelle si le code est illisible"),
        latitude: float | None = Form(default=None, ge=-90, le=90),
        longitude: float | None = Form(default=None, ge=-180, le=180),
        utilisateur: Utilisateur = Depends(utilisateur_courant),
        db: Session = Depends(get_db)):
    """Enregistre la reception ou l'expedition d'une unite, a partir de l'image de son code ou de son identifiant saisi."""
    if typeOperation not in (TypeOperation.reception, TypeOperation.expedition):
        raise HTTPException(422, "Operation non geree ici: reception ou expedition seulement.")
    if typeOperation not in OPERATIONS_AUTORISEES.get(utilisateur.structure.type, set()):
        raise HTTPException(403, "Votre structure n'est pas autorisee a enregistrer cette operation.")
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "Fournissez la latitude et la longitude ensemble, ou aucune des deux.")

    # Etapes 1 a 3: lecture du code (ou saisie manuelle), puis verification dans la base centrale
    unite = await obtenir_unite(db, image, numeroSerie)

    # Etapes 4 et 5: construction et enregistrement de l'evenement
    evenement = Evenement(typeOperation=typeOperation, latitude=latitude, longitude=longitude,
                          numeroSerie=unite.numeroSerie, utilisateur_id=utilisateur.id)
    db.add(evenement)

    # Variante 3b: unite deja desactivee, l'evenement est enregistre avec une alerte a verifier
    alerte = unite.statut == StatutUnite.desactivee
    if alerte:
        db.add(Anomalie(typeAnomalie=TypeAnomalie.reutilisationIdentifiant, score=1.0,
                        evenement=evenement))
    db.commit()
    db.refresh(evenement)

    message = ("Enregistre avec une alerte: identifiant deja desactive, a verifier."
               if alerte else "Evenement enregistre.")
    return EvenementSortie(id=evenement.id, numeroSerie=evenement.numeroSerie,
                           typeOperation=evenement.typeOperation, dateHeure=evenement.dateHeure,
                           latitude=evenement.latitude, longitude=evenement.longitude,
                           alerte=alerte, message=message,
                           methodeLecture=getattr(unite, "methode_lecture", None))
