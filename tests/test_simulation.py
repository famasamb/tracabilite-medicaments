"""Tests de la simulation de l'historique normal (phase 3)."""
from datetime import datetime

import numpy as np

from app.models import TypeOperation, TypeStructure
from app.routes_evenements import OPERATIONS_AUTORISEES
from jeu_de_donnees.geographie import VILLES, distance_km
from jeu_de_donnees.simulation import Acteur, simuler_historique

DEBUT, FIN = datetime(2026, 8, 3, 8, 0), datetime(2026, 10, 5, 23, 59)
CIRCUIT = [("expedition", "fabricant"), ("reception", "grossisteRepartiteur"),
           ("expedition", "grossisteRepartiteur"), ("reception", "SR"), ("expedition", "SR"),
           ("reception", "officine"), ("dispensation", "officine")]


def acteur(id_, type_, ville):
    return Acteur(id_, type_, ville, VILLES[ville])


def simuler(graine=7):
    lots = {"L1": [f"A{i:03d}" for i in range(40)], "L2": [f"B{i:03d}" for i in range(40)],
            "L3": [f"C{i:03d}" for i in range(40)]}
    fabricant = acteur("fab", "fabricant", "Dakar")
    grossistes = [acteur("g1", "grossisteRepartiteur", "Dakar"), acteur("g2", "grossisteRepartiteur", "Kaolack")]
    srs = {v: acteur(f"sr-{v}", "SR", v) for v in ("Dakar", "Thies", "Ziguinchor")}
    officines = [acteur("o1", "officine", "Dakar"), acteur("o2", "officine", "Thies"),
                 acteur("o3", "officine", "Ziguinchor")]
    evenements = simuler_historique(lots, fabricant, grossistes, srs, officines, DEBUT, FIN,
                                    np.random.default_rng(graine))
    types = {a.id: a.type for a in [fabricant, *grossistes, *srs.values(), *officines]}
    return evenements, types


def par_unite(evenements):
    resultat = {}
    for e in evenements:
        resultat.setdefault(e.numeroSerie, []).append(e)
    return resultat


def test_chaque_unite_suit_le_circuit_de_la_fiche_7():
    evenements, types = simuler()
    assert evenements
    for liste in par_unite(evenements).values():
        suite = [(e.typeOperation, types[e.acteur_id]) for e in liste]
        assert suite == CIRCUIT[:len(suite)]          # un debut du circuit, dans l'ordre


def test_chaque_acteur_ne_fait_que_ce_que_la_fiche_7_lui_permet():
    evenements, types = simuler()
    for e in evenements:
        operation = TypeOperation(e.typeOperation)
        if operation != TypeOperation.dispensation:
            assert operation in OPERATIONS_AUTORISEES[TypeStructure(types[e.acteur_id])]
        else:
            assert types[e.acteur_id] == "officine"


def test_les_dates_sont_dans_la_periode_et_triees():
    evenements, _ = simuler()
    dates = [e.dateHeure for e in evenements]
    assert dates == sorted(dates) and DEBUT <= dates[0] and dates[-1] <= FIN


def test_une_unite_n_est_dispensee_qu_une_fois_et_rien_ne_suit():
    evenements, _ = simuler()
    for liste in par_unite(evenements).values():
        operations = [e.typeOperation for e in liste]
        assert operations.count("dispensation") <= 1
        if "dispensation" in operations:
            assert operations[-1] == "dispensation"


def test_les_deplacements_d_une_unite_sont_plausibles():
    evenements, _ = simuler()
    for liste in par_unite(evenements).values():
        for avant, apres in zip(liste, liste[1:]):
            heures = (apres.dateHeure - avant.dateHeure).total_seconds() / 3600
            km = distance_km((avant.latitude, avant.longitude), (apres.latitude, apres.longitude))
            assert heures > 0 and km / heures < 100        # km/h


def test_les_positions_sont_au_senegal():
    evenements, _ = simuler()
    assert all(12 < e.latitude < 17 and -18 < e.longitude < -11 for e in evenements)


def test_une_partie_des_unites_est_dispensee_et_une_partie_encore_en_circuit():
    evenements, _ = simuler()
    series = par_unite(evenements)
    dispensees = sum(1 for liste in series.values() if liste[-1].typeOperation == "dispensation")
    assert 0 < dispensees < len(series)


def test_meme_graine_meme_historique():
    assert simuler(3)[0] == simuler(3)[0] and simuler(3)[0] != simuler(4)[0]