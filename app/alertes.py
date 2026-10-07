"""Alertes regroupees pour l'affichage (phase 5, fin).

Le moteur ecrit une ligne Anomalie par evenement concerne. Pour la reutilisation, la rupture et le trajet,
une ligne est bien une alerte: une unite, un evenement. Pour la concentration inhabituelle, une seule
situation (une officine, un lot) touche des dizaines ou des centaines d'evenements: la personne qui
verifie doit voir UNE alerte, avec le nombre d'evenements concernes.

Ce module ne fait que lire: aucune ligne n'est modifiee.
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from .models import Anomalie, Evenement, Lot, Structure, TypeAnomalie, Unite, Utilisateur


@dataclass(frozen=True)
class Alerte:
    typeAnomalie: TypeAnomalie
    statut: str
    dateDetection: datetime        # la plus recente du groupe
    structure: str                 # nom de la structure qui a enregistre l'evenement
    numeroSerie: str | None        # None pour une concentration (plusieurs unites)
    numeroLot: str | None
    evenements: int                # nombre d'evenements (donc de lignes Anomalie) couverts par l'alerte
    score: float                   # le plus eleve du groupe


def alertes_regroupees(db: Session) -> list[Alerte]:
    """Une alerte par anomalie, sauf la concentration: une alerte par (structure, lot, statut).

    Triees de la plus recente a la plus ancienne."""
    lignes = (db.query(Anomalie, Structure.id, Structure.nom, Unite.lot_id, Lot.numeroLot, Evenement.numeroSerie)
              .join(Evenement, Anomalie.evenement_id == Evenement.id)
              .join(Utilisateur, Evenement.utilisateur_id == Utilisateur.id)
              .join(Structure, Utilisateur.structure_id == Structure.id)
              .outerjoin(Unite, Evenement.numeroSerie == Unite.numeroSerie)
              .outerjoin(Lot, Unite.lot_id == Lot.id).all())
    groupes: dict[tuple, list] = {}
    for anomalie, structure_id, nom, lot_id, numero_lot, serie in lignes:
        if anomalie.typeAnomalie == TypeAnomalie.concentrationInhabituelle:
            cle = (anomalie.typeAnomalie, structure_id, lot_id, anomalie.statut)
        else:
            cle = (anomalie.id,)
        groupes.setdefault(cle, []).append((anomalie, nom, numero_lot, serie))

    alertes = []
    for membres in groupes.values():
        premiere, nom, numero_lot, serie = membres[0]
        groupe = premiere.typeAnomalie == TypeAnomalie.concentrationInhabituelle
        alertes.append(Alerte(
            premiere.typeAnomalie, premiere.statut, max(m[0].dateDetection for m in membres), nom,
            None if groupe else serie, numero_lot, len(membres), max(m[0].score for m in membres)))
    return sorted(alertes, key=lambda a: a.dateDetection, reverse=True)