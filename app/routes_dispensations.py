"""Cas d'utilisation Enregistrer la dispensation (fiche 8)."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .auth import utilisateur_courant
from .db import get_db
from .models import (Anomalie, Evenement, StatutUnite, TypeAnomalie, TypeOperation,
                     TypeStructure, Utilisateur)
from .routes_evenements import obtenir_unite
from .schemas import EvenementSortie

router = APIRouter(prefix="/dispensations", tags=["Dispensation"])


def _receptionnee_par(db: Session, numero_serie: str, structure_id: str) -> bool:
    """Vrai si l'historique de l'unite contient une reception faite par cette structure."""
    return db.query(Evenement).join(Utilisateur, Evenement.utilisateur_id == Utilisateur.id).filter(
        Evenement.numeroSerie == numero_serie,
        Evenement.typeOperation == TypeOperation.reception,
        Utilisateur.structure_id == structure_id).first() is not None


@router.post("", response_model=EvenementSortie, status_code=201)
async def enregistrer_dispensation(
        image: UploadFile | None = File(default=None, description="Photo du code DataMatrix"),
        numeroSerie: str | None = Form(default=None, description="Saisie manuelle si le code est illisible"),
        latitude: float | None = Form(default=None, ge=-90, le=90),
        longitude: float | None = Form(default=None, ge=-180, le=180),
        utilisateur: Utilisateur = Depends(utilisateur_courant),
        db: Session = Depends(get_db)):
    """Enregistre la remise d'une unite au patient et desactive definitivement son identifiant."""
    if utilisateur.structure.type != TypeStructure.officine:
        raise HTTPException(403, "La dispensation est reservee aux officines.")
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "Fournissez la latitude et la longitude ensemble, ou aucune des deux.")

    # Etapes 1 et 2: lecture du code (ou saisie manuelle)
    unite = await obtenir_unite(db, image, numeroSerie)

    # Etape 4: construction de l'evenement de dispensation
    evenement = Evenement(typeOperation=TypeOperation.dispensation, latitude=latitude,
                          longitude=longitude, numeroSerie=unite.numeroSerie,
                          utilisateur_id=utilisateur.id)
    db.add(evenement)

    # Variante 3b: identifiant deja desactive. Reutilisation possible: la dispensation n'est pas
    # validee, l'evenement est garde avec une alerte a verifier, et le scenario s'arrete.
    if unite.statut == StatutUnite.desactivee:
        db.add(Anomalie(typeAnomalie=TypeAnomalie.reutilisationIdentifiant, score=1.0,
                        evenement=evenement))
        db.commit()
        raise HTTPException(409, "Dispensation non validee: cet identifiant est deja desactive. "
                                 "Reutilisation possible, une alerte est soumise a verification.")

    # Variante 3c: aucune reception par cette officine dans l'historique (rupture de sequence).
    # La dispensation peut se poursuivre, sous reserve de verification.
    alerte = not _receptionnee_par(db, unite.numeroSerie, utilisateur.structure_id)
    if alerte:
        db.add(Anomalie(typeAnomalie=TypeAnomalie.ruptureSequence, score=1.0, evenement=evenement))

    # Etapes 5 et 6: enregistrement et desactivation definitive de l'identifiant
    unite.statut = StatutUnite.desactivee
    db.commit()
    db.refresh(evenement)

    message = ("Dispensation enregistree avec une alerte: aucune reception par cette officine "
               "dans l'historique, a verifier." if alerte else "Dispensation enregistree.")
    return EvenementSortie(id=evenement.id, numeroSerie=evenement.numeroSerie,
                           typeOperation=evenement.typeOperation, dateHeure=evenement.dateHeure,
                           latitude=evenement.latitude, longitude=evenement.longitude,
                           alerte=alerte, message=message,
                           methodeLecture=getattr(unite, "methode_lecture", None))
