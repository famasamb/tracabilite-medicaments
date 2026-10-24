"""Cas d'utilisation Enregistrer la reception / Enregistrer l'expedition (fiche 7): la route HTTP.

Les regles metier sont dans app/services/evenements.py."""
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import EvenementSortie
from app.api.televersement import lire_televersement
from app.core.auth import utilisateur_courant
from app.core.db import get_db
from app.domaine.models import Evenement, TypeAnomalie, TypeOperation, Utilisateur
from app.services.evenements import (MESSAGE_BOITE_HORS_CARTON, creer_evenement, identifier_unite,
                                     verifier_droit_operation)
from app.services.horsligne import evenement_deja_enregistre, verifier_identifiant_client

router = APIRouter(prefix="/evenements", tags=["Evenements"])


def sortie_d_un_evenement_existant(evenement: Evenement) -> EvenementSortie:
    """Resultat d'une operation deja enregistree, reconstruit depuis la base (envoi repete)."""
    anomalie = evenement.anomalies[0] if evenement.anomalies else None
    if evenement.typeOperation == TypeOperation.dispensation and anomalie is not None \
            and anomalie.typeAnomalie == TypeAnomalie.reutilisationIdentifiant:
        raise HTTPException(409, "Dispensation non validee: cet identifiant est deja desactive. "
                                 "Reutilisation possible, une alerte est soumise a verification.")
    if anomalie is None:
        message = "Dispensation enregistree." if evenement.typeOperation == TypeOperation.dispensation else "Evenement enregistre."
    elif anomalie.typeAnomalie == TypeAnomalie.reutilisationIdentifiant:
        message = "Enregistre avec une alerte: identifiant deja desactive, a verifier."
    elif anomalie.typeAnomalie == TypeAnomalie.boiteHorsCarton:
        message = MESSAGE_BOITE_HORS_CARTON
    elif evenement.typeOperation == TypeOperation.dispensation:
        message = ("Dispensation enregistree avec une alerte: aucune reception par cette officine "
                   "dans l'historique, a verifier.")
    else:
        message = "Enregistre avec une alerte: aucune expedition de cette unite dans l'historique, a verifier."
    return EvenementSortie(id=evenement.id, numeroSerie=evenement.numeroSerie,
                           typeOperation=evenement.typeOperation, dateHeure=evenement.dateHeure,
                           latitude=evenement.latitude, longitude=evenement.longitude,
                           alerte=anomalie is not None, message=message,
                           typeAnomalie=anomalie.typeAnomalie.value if anomalie else None)


@router.post("", response_model=EvenementSortie, status_code=201)
async def enregistrer_evenement(
        typeOperation: TypeOperation = Form(description="reception ou expedition"),
        image: UploadFile | None = File(default=None, description="Photo du code DataMatrix"),
        numeroSerie: str | None = Form(default=None, description="Saisie manuelle si le code est illisible"),
        latitude: float | None = Form(default=None, ge=-90, le=90),
        longitude: float | None = Form(default=None, ge=-180, le=180),
        dateHeure: datetime | None = Form(default=None, description="Date reelle de l'operation (operation faite sans reseau)"),
        identifiantClient: str | None = Form(default=None, description="Identifiant fabrique par le telephone"),
        reponse: Response = None,
        utilisateur: Utilisateur = Depends(utilisateur_courant),
        db: Session = Depends(get_db)):
    """Enregistre la reception ou l'expedition d'une unite, a partir de l'image de son code ou de son identifiant saisi."""
    if typeOperation not in (TypeOperation.reception, TypeOperation.expedition):
        raise HTTPException(422, "Operation non geree ici: reception ou expedition seulement.")
    verifier_droit_operation(utilisateur, typeOperation)
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "Fournissez la latitude et la longitude ensemble, ou aucune des deux.")

    # Operation deja recue (envoi repete apres une coupure): on renvoie le meme resultat, sans doublon
    identifiantClient = verifier_identifiant_client(identifiantClient)
    existant = evenement_deja_enregistre(db, utilisateur, identifiantClient)
    if existant is not None:
        reponse.status_code = 200
        return sortie_d_un_evenement_existant(existant)

    # Etapes 1 a 3: lecture du code (ou saisie manuelle), puis verification dans la base centrale
    unite = await identifier_unite(db, await lire_televersement(image), numeroSerie)

    # Etapes 4 et 5: construction et enregistrement de l'evenement (avec l'alerte eventuelle)
    evenement, type_anomalie, message = creer_evenement(
        db, utilisateur, unite, typeOperation, latitude, longitude, dateHeure, identifiantClient)
    alerte = type_anomalie is not None
    db.commit()
    db.refresh(evenement)

    return EvenementSortie(id=evenement.id, numeroSerie=evenement.numeroSerie,
                           typeOperation=evenement.typeOperation, dateHeure=evenement.dateHeure,
                           latitude=evenement.latitude, longitude=evenement.longitude,
                           alerte=alerte, message=message,
                           typeAnomalie=type_anomalie.value if type_anomalie else None,
                           methodeLecture=getattr(unite, "methode_lecture", None))
