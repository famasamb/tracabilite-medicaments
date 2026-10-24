"""Cas d'utilisation Enregistrer la dispensation (fiche 8): la route HTTP.

Les regles metier sont dans app/services/dispensations.py."""
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.evenements import sortie_d_un_evenement_existant
from app.api.schemas import EvenementSortie
from app.api.televersement import lire_televersement
from app.core.auth import utilisateur_courant
from app.core.db import get_db
from app.domaine.models import Utilisateur
from app.services.dispensations import enregistrer_dispensation, verifier_officine
from app.services.evenements import identifier_unite
from app.services.horsligne import evenement_deja_enregistre, verifier_identifiant_client

router = APIRouter(prefix="/dispensations", tags=["Dispensation"])


@router.post("", response_model=EvenementSortie, status_code=201)
async def enregistrer_une_dispensation(
        image: UploadFile | None = File(default=None, description="Photo du code DataMatrix"),
        numeroSerie: str | None = Form(default=None, description="Saisie manuelle si le code est illisible"),
        latitude: float | None = Form(default=None, ge=-90, le=90),
        longitude: float | None = Form(default=None, ge=-180, le=180),
        dateHeure: datetime | None = Form(default=None, description="Date reelle de l'operation (operation faite sans reseau)"),
        identifiantClient: str | None = Form(default=None, description="Identifiant fabrique par le telephone"),
        reponse: Response = None,
        utilisateur: Utilisateur = Depends(utilisateur_courant),
        db: Session = Depends(get_db)):
    """Enregistre la remise d'une unite au patient et desactive definitivement son identifiant."""
    verifier_officine(utilisateur)
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "Fournissez la latitude et la longitude ensemble, ou aucune des deux.")

    # Operation deja recue (envoi repete apres une coupure): meme resultat, sans doublon
    identifiantClient = verifier_identifiant_client(identifiantClient)
    existant = evenement_deja_enregistre(db, utilisateur, identifiantClient)
    if existant is not None:
        reponse.status_code = 200
        return sortie_d_un_evenement_existant(existant)

    unite = await identifier_unite(db, await lire_televersement(image), numeroSerie)
    resultat = enregistrer_dispensation(db, utilisateur, unite, latitude, longitude, dateHeure, identifiantClient)
    evenement = resultat.evenement
    return EvenementSortie(id=evenement.id, numeroSerie=evenement.numeroSerie,
                           typeOperation=evenement.typeOperation, dateHeure=evenement.dateHeure,
                           latitude=evenement.latitude, longitude=evenement.longitude,
                           alerte=resultat.alerte, message=resultat.message,
                           typeAnomalie=resultat.type_anomalie,
                           methodeLecture=getattr(unite, "methode_lecture", None))
