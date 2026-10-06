"""Cas d'utilisation Consulter le statut d'une unite (fiche 9). Aucune donnee n'est modifiee."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .auth import utilisateur_courant
from .db import get_db
from .models import Anomalie, Evenement, TypeStructure, Utilisateur
from .routes_evenements import obtenir_unite
from .schemas import AnomalieAssociee, DernierEvenement, StatutUniteSortie

router = APIRouter(prefix="/unites", tags=["Unites"])

# Acteurs de la fiche 9 (la PNA n'y figure pas)
STRUCTURES_AUTORISEES = {TypeStructure.fabricant, TypeStructure.grossisteRepartiteur,
                         TypeStructure.SR, TypeStructure.officine}


@router.post("/statut", response_model=StatutUniteSortie)
async def consulter_statut(
        image: UploadFile | None = File(default=None, description="Photo du code DataMatrix"),
        numeroSerie: str | None = Form(default=None, description="Saisie manuelle si le code est illisible"),
        utilisateur: Utilisateur = Depends(utilisateur_courant),
        db: Session = Depends(get_db)):
    """Donne le statut d'une unite, son dernier evenement connu et l'anomalie associee, s'il y en a une."""
    if utilisateur.structure.type not in STRUCTURES_AUTORISEES:
        raise HTTPException(403, "Votre structure n'est pas autorisee a consulter le statut d'une unite.")

    # Etapes 1 et 2: lecture du code (ou saisie manuelle), recherche dans la base
    try:
        unite = await obtenir_unite(db, image, numeroSerie)
    except HTTPException as erreur:
        if erreur.status_code == 404:  # variante 2b
            raise HTTPException(404, "Cette unite n'est pas referencee: verifiez sa provenance.")
        raise

    # Un fabricant ne consulte que les unites qu'il a serialisees
    if (utilisateur.structure.type == TypeStructure.fabricant
            and unite.lot.produit.laboratoire != utilisateur.structure.nom):
        raise HTTPException(403, "Cette unite n'a pas ete serialisee par votre structure.")

    # Etape 3: statut, dernier evenement connu, anomalie associee
    dernier = (db.query(Evenement).filter(Evenement.numeroSerie == unite.numeroSerie)
               .order_by(Evenement.dateHeure.desc()).first())
    anomalie = (db.query(Anomalie).join(Evenement, Anomalie.evenement_id == Evenement.id)
                .filter(Evenement.numeroSerie == unite.numeroSerie)
                .order_by(Anomalie.dateDetection.desc()).first())
    return StatutUniteSortie(
        numeroSerie=unite.numeroSerie, statut=unite.statut,
        dernierEvenement=DernierEvenement(
            typeOperation=dernier.typeOperation, dateHeure=dernier.dateHeure,
            latitude=dernier.latitude, longitude=dernier.longitude) if dernier else None,
        anomalie=AnomalieAssociee(
            typeAnomalie=anomalie.typeAnomalie, statut=anomalie.statut,
            dateDetection=anomalie.dateDetection) if anomalie else None)