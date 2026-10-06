"""Cas d'utilisation Consulter le tableau de bord du circuit public (fiche 10). Aucune donnee n'est modifiee."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from .db import get_db
from .models import Anomalie, Evenement, Structure, TypeStructure, Utilisateur
from .routes_sr import pna_courante
from .schemas import (AlerteRecente, FiltreTableau, PointCarte, TableauDeBordSortie)

router = APIRouter(prefix="/tableau-de-bord", tags=["Tableau de bord"])

AVERTISSEMENT = ("Les alertes sont des signaux a verifier par une personne, "
                 "pas des fraudes confirmees.")
MAX_POINTS_CARTE = 1000
MAX_ALERTES = 20


def _evenements_des_sr(db: Session, pna: Utilisateur, entites):
    """Requete sur les evenements faits par des utilisateurs des SR rattaches a cette PNA."""
    return (db.query(*entites).select_from(Evenement)
            .join(Utilisateur, Evenement.utilisateur_id == Utilisateur.id)
            .join(Structure, Utilisateur.structure_id == Structure.id)
            .filter(Structure.mere_id == pna.structure_id, Structure.type == TypeStructure.SR))


def _filtrer(requete, sr_id: str | None, du: date | None, au: date | None, colonne_date):
    if sr_id:
        requete = requete.filter(Structure.id == sr_id)
    if du:
        requete = requete.filter(colonne_date >= datetime.combine(du, datetime.min.time()))
    if au:  # la date de fin est incluse
        requete = requete.filter(colonne_date < datetime.combine(au + timedelta(days=1), datetime.min.time()))
    return requete


@router.get("", response_model=TableauDeBordSortie)
def consulter_tableau_de_bord(
        sr_id: str | None = Query(default=None, description="Filtrer sur un SR"),
        du: date | None = Query(default=None, description="Date de debut (incluse)"),
        au: date | None = Query(default=None, description="Date de fin (incluse)"),
        pna: Utilisateur = Depends(pna_courante), db: Session = Depends(get_db)):
    """Vue d'ensemble de l'activite des SR de la PNA, filtrable par SR et par periode."""
    if du and au and du > au:
        raise HTTPException(422, "La date de debut doit preceder la date de fin.")
    if sr_id:
        sr = db.get(Structure, sr_id)
        if sr is None or sr.type != TypeStructure.SR or sr.mere_id != pna.structure_id:
            raise HTTPException(404, "SR introuvable parmi les services regionaux de votre PNA.")

    # Etape 2: regrouper les evenements enregistres dans les SR
    evenements = _filtrer(_evenements_des_sr(db, pna, [Evenement]), sr_id, du, au, Evenement.dateHeure)
    nombre = evenements.count()
    filtre = FiltreTableau(srId=sr_id, du=du, au=au)
    if nombre == 0:  # variante 4b
        return TableauDeBordSortie(
            avertissement=AVERTISSEMENT, filtre=filtre,
            message="Aucun evenement pour ce SR ou cette periode. Modifiez votre filtre.",
            nombreEvenements=0, unitesSuivies=0, anomaliesSignalees=0, anomaliesParType={},
            pointsCarte=[], alertesRecentes=[])

    # Etape 3: vue d'ensemble
    unites = _filtrer(_evenements_des_sr(db, pna, [func.count(distinct(Evenement.numeroSerie))]),
                      sr_id, du, au, Evenement.dateHeure).scalar()
    anomalies = (_filtrer(
        _evenements_des_sr(db, pna, [Anomalie.typeAnomalie, Anomalie.statut, Anomalie.dateDetection,
                                     Structure.nom, Evenement.numeroSerie])
        .join(Anomalie, Anomalie.evenement_id == Evenement.id),
        sr_id, du, au, Evenement.dateHeure)
        .order_by(Anomalie.dateDetection.desc()).all())
    par_type: dict[str, int] = {}
    for a in anomalies:
        par_type[a.typeAnomalie.value] = par_type.get(a.typeAnomalie.value, 0) + 1
    points = (_filtrer(
        _evenements_des_sr(db, pna, [Evenement.latitude, Evenement.longitude, Evenement.typeOperation,
                                     Evenement.dateHeure, Structure.nom])
        .filter(Evenement.latitude.isnot(None), Evenement.longitude.isnot(None)),
        sr_id, du, au, Evenement.dateHeure)
        .order_by(Evenement.dateHeure.desc()).limit(MAX_POINTS_CARTE).all())

    return TableauDeBordSortie(
        avertissement=AVERTISSEMENT, filtre=filtre, message=None,
        nombreEvenements=nombre, unitesSuivies=unites,
        anomaliesSignalees=len(anomalies), anomaliesParType=par_type,
        pointsCarte=[PointCarte(latitude=p.latitude, longitude=p.longitude,
                                typeOperation=p.typeOperation, dateHeure=p.dateHeure, sr=p.nom)
                     for p in points],
        alertesRecentes=[AlerteRecente(typeAnomalie=a.typeAnomalie, statut=a.statut,
                                       dateDetection=a.dateDetection, sr=a.nom,
                                       numeroSerie=a.numeroSerie) for a in anomalies[:MAX_ALERTES]])