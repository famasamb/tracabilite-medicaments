"""Simulation de l'historique normal du circuit (phase 3): fabricant, grossiste, SR, officine.

Le circuit suit la fiche 7: le fabricant expedie; le grossiste recoit et expedie; le SR recoit et
expedie; l'officine recoit puis dispense. Aucune anomalie n'est produite ici.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from .geographie import distance_km

VITESSE_KMH = 45.0      # vitesse moyenne d'un camion de livraison
FACTEUR_ROUTE = 1.3     # la route est plus longue que la ligne droite
PART_DISPENSEE = 0.85   # part des unites remises au patient (les autres restent en stock)


@dataclass(frozen=True)
class Acteur:
    id: str
    type: str                         # fabricant, grossisteRepartiteur, SR, officine
    ville: str
    position: tuple[float, float]     # (latitude, longitude) habituelle de la structure


@dataclass(frozen=True)
class EvenementSimule:
    numeroSerie: str
    typeOperation: str                # reception, expedition, dispensation
    dateHeure: datetime
    latitude: float
    longitude: float
    acteur_id: str


def _ouvrable(instant: datetime, g: np.random.Generator) -> datetime:
    """Ramene un instant dans la journee de travail (8 h a 17 h environ)."""
    if instant.hour >= 17:
        instant = (instant + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    elif instant.hour < 8:
        instant = instant.replace(hour=8, minute=0, second=0, microsecond=0)
    return instant + timedelta(minutes=int(g.integers(0, 90)))


def _trajet(a: Acteur, b: Acteur, g: np.random.Generator) -> timedelta:
    """Duree de livraison: temps de route plus chargement et dechargement."""
    route = distance_km(a.position, b.position) * FACTEUR_ROUTE / VITESSE_KMH
    return timedelta(hours=route + float(g.uniform(2, 30)))


def _gps(acteur: Acteur, g: np.random.Generator) -> tuple[float, float]:
    """Position releveee par le telephone: la position de la structure, a quelques metres pres."""
    return (acteur.position[0] + float(g.uniform(-0.0015, 0.0015)),
            acteur.position[1] + float(g.uniform(-0.0015, 0.0015)))


def _balayer(series: list[str], acteur: Acteur, operation: str, debut: datetime,
             g: np.random.Generator, sortie: list[EvenementSimule]) -> datetime:
    """Scanne les unites une par une (6 a 15 secondes entre deux). Renvoie l'heure du dernier scan."""
    instant = dernier = debut
    for serie in series:
        latitude, longitude = _gps(acteur, g)
        sortie.append(EvenementSimule(serie, operation, instant, latitude, longitude, acteur.id))
        dernier = instant
        instant = instant + timedelta(seconds=float(g.uniform(6, 15)))
    return dernier


def simuler_historique(lots: dict[str, list[str]], fabricant: Acteur, grossistes: list[Acteur],
                       srs: dict[str, Acteur], officines: list[Acteur], debut: datetime,
                       fin: datetime, g: np.random.Generator) -> list[EvenementSimule]:
    """Produit les evenements normaux de tous les lots, jusqu'a la date `fin` (incluse).

    `lots` associe un numero de lot a la liste de ses numeros de serie; `srs` associe une ville a son SR.
    Un lot part tous les 4 jours. Les unites encore en circuit a la date `fin` n'ont que les
    evenements deja survenus.
    """
    villes = sorted({o.ville for o in officines})
    manquantes = [v for v in villes if v not in srs]
    if manquantes:
        raise ValueError(f"pas de SR pour: {manquantes}")
    evenements: list[EvenementSimule] = []

    for i, series in enumerate(lots.values()):
        grossiste = grossistes[int(g.integers(len(grossistes)))]
        # Chaque unite est destinee a une officine, via le SR de sa region
        destination: dict[str, dict[str, list[str]]] = {}
        for serie in series:
            ville = villes[int(g.integers(len(villes)))]
            choix = [o for o in officines if o.ville == ville]
            officine = choix[int(g.integers(len(choix)))]
            destination.setdefault(ville, {}).setdefault(officine.id, []).append(serie)

        fin_exp = _balayer(series, fabricant, "expedition",
                           _ouvrable(debut + timedelta(days=4 * i), g), g, evenements)
        fin_rec = _balayer(series, grossiste, "reception",
                           _ouvrable(fin_exp + _trajet(fabricant, grossiste, g), g), g, evenements)

        for ville, par_officine in destination.items():
            sr = srs[ville]
            du_sr = [s for liste in par_officine.values() for s in liste]
            fin_exp_g = _balayer(du_sr, grossiste, "expedition",
                                 _ouvrable(fin_rec + timedelta(hours=float(g.uniform(6, 48))), g),
                                 g, evenements)
            fin_rec_sr = _balayer(du_sr, sr, "reception",
                                  _ouvrable(fin_exp_g + _trajet(grossiste, sr, g), g), g, evenements)
            for officine_id, liste in par_officine.items():
                officine = next(o for o in officines if o.id == officine_id)
                fin_exp_sr = _balayer(liste, sr, "expedition",
                                      _ouvrable(fin_rec_sr + timedelta(hours=float(g.uniform(2, 48))), g),
                                      g, evenements)
                fin_rec_o = _balayer(liste, officine, "reception",
                                     _ouvrable(fin_exp_sr + _trajet(sr, officine, g), g), g, evenements)
                for serie in liste:
                    if g.random() < PART_DISPENSEE:
                        quand = _ouvrable(fin_rec_o + timedelta(days=float(g.uniform(1, 25))), g)
                        latitude, longitude = _gps(officine, g)
                        evenements.append(EvenementSimule(serie, "dispensation", quand,
                                                          latitude, longitude, officine.id))

    return sorted((e for e in evenements if e.dateHeure <= fin), key=lambda e: e.dateHeure)