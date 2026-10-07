"""Tests de l'injection d'anomalies dans l'historique (phase 3).

Un mini controle de regles, ecrit ici pour les tests seulement, verifie que l'historique normal ne
contient aucune de ces anomalies et que chaque anomalie injectee est bien detectable.
"""
from datetime import datetime

import numpy as np
import pytest

from jeu_de_donnees.anomalies import (DISTANCE_TRAJET_MIN_KM, injecter_reutilisations,
                                      injecter_ruptures, injecter_trajets)
from jeu_de_donnees.geographie import VILLES, distance_km
from jeu_de_donnees.simulation import Acteur, simuler_historique

DEBUT, FIN = datetime(2026, 8, 3, 8, 0), datetime(2026, 10, 5, 23, 59)
VILLES_OFFICINES = ["Dakar", "Thies", "Ziguinchor", "Saint-Louis", "Tambacounda", "Kaolack"]


def acteur(id_, type_, ville):
    return Acteur(id_, type_, ville, VILLES[ville])


def monde(graine=11):
    lots = {f"L{i}": [f"L{i}U{j:03d}" for j in range(40)] for i in range(8)}
    fabricant = acteur("fab", "fabricant", "Dakar")
    grossistes = [acteur("g1", "grossisteRepartiteur", "Dakar")]
    srs = {v: acteur(f"sr-{v}", "SR", v) for v in VILLES_OFFICINES}
    officines = [acteur(f"o-{v}", "officine", v) for v in VILLES_OFFICINES]
    g = np.random.default_rng(graine)
    normal = simuler_historique(lots, fabricant, grossistes, srs, officines, DEBUT, FIN, g)
    acteurs = {a.id: a for a in [fabricant, *grossistes, *srs.values(), *officines]}
    return normal, acteurs, g


def anomalies_par_regles(evenements, acteurs):
    """Applique trois regles simples et renvoie {type: ensemble d'evenements signales}."""
    signales = {"reutilisationIdentifiant": set(), "ruptureSequence": set(), "trajetInhabituel": set()}
    par_unite = {}
    for e in sorted(evenements, key=lambda e: e.dateHeure):
        par_unite.setdefault(e.numeroSerie, []).append(e)
    for liste in par_unite.values():
        for i, e in enumerate(liste):
            if any(avant.typeOperation == "dispensation" for avant in liste[:i]):
                signales["reutilisationIdentifiant"].add(e)
            if e.typeOperation == "dispensation" and not any(
                    avant.typeOperation == "reception" and avant.acteur_id == e.acteur_id for avant in liste[:i]):
                signales["ruptureSequence"].add(e)
            if i > 0:
                avant = liste[i - 1]
                heures = (e.dateHeure - avant.dateHeure).total_seconds() / 3600
                km = distance_km((avant.latitude, avant.longitude), (e.latitude, e.longitude))
                if km >= 50 and km / heures > 120:
                    signales["trajetInhabituel"].add(e)
    return signales


def injecter(graine=11, n=4):
    normal, acteurs, g = monde(graine)
    deja: set[str] = set()
    injections = (injecter_reutilisations(normal, acteurs, n, FIN, g, deja)
                  + injecter_ruptures(normal, acteurs, n, FIN, g, deja)
                  + injecter_trajets(normal, acteurs, n, FIN, g, deja))
    return normal, acteurs, injections


def test_l_historique_normal_ne_contient_aucune_anomalie():
    normal, acteurs, _ = monde()
    assert all(not s for s in anomalies_par_regles(normal, acteurs).values())


def test_chaque_anomalie_injectee_est_detectee_et_seulement_elle():
    normal, acteurs, injections = injecter()
    signales = anomalies_par_regles(normal + [i.evenement for i in injections], acteurs)
    for type_ in signales:
        attendus = {i.evenement for i in injections if i.type == type_}
        assert len(attendus) == 4
        assert signales[type_] == attendus


def test_les_unites_injectees_sont_toutes_differentes_et_dans_la_periode():
    _, _, injections = injecter()
    series = [i.evenement.numeroSerie for i in injections]
    assert len(series) == len(set(series)) == 12
    assert all(DEBUT <= i.evenement.dateHeure <= FIN for i in injections)


def test_le_trajet_inhabituel_est_net():
    normal, acteurs, injections = injecter()
    derniers = {e.numeroSerie: e for e in sorted(normal, key=lambda e: e.dateHeure)}
    for i in (i for i in injections if i.type == "trajetInhabituel"):
        avant = derniers[i.evenement.numeroSerie]
        heures = (i.evenement.dateHeure - avant.dateHeure).total_seconds() / 3600
        km = distance_km((avant.latitude, avant.longitude), (i.evenement.latitude, i.evenement.longitude))
        assert heures < 1 and km > DISTANCE_TRAJET_MIN_KM - 10      # a quelques centaines de metres pres


def test_meme_graine_memes_injections():
    assert injecter(5)[2] == injecter(5)[2]


def test_trop_d_anomalies_demandees_est_refuse():
    normal, acteurs, g = monde()
    with pytest.raises(ValueError):
        injecter_ruptures(normal, acteurs, 10_000, FIN, g, set())