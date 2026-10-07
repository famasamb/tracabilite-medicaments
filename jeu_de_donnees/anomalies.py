"""Injection d'anomalies dans un historique normal (phase 3 de la methodologie).

Chaque anomalie est un evenement ajoute a l'historique, avec sa verite terrain. Les cas sont
volontairement nets: aucun seuil n'est suppose, c'est au moteur de la phase 5 de les retrouver.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from .geographie import distance_km
from .simulation import Acteur, EvenementSimule, _gps, _ouvrable

DISTANCE_TRAJET_MIN_KM = 200   # une unite "voyage" d'au moins 200 km en moins d'une heure


@dataclass(frozen=True)
class Injection:
    type: str                     # un des types de TypeAnomalie
    evenement: EvenementSimule    # l'evenement ajoute, celui qui revele l'anomalie
    description: str


def _derniers(evenements: list[EvenementSimule]) -> dict[str, EvenementSimule]:
    """Dernier evenement de chaque unite."""
    resultat: dict[str, EvenementSimule] = {}
    for e in sorted(evenements, key=lambda e: e.dateHeure):
        resultat[e.numeroSerie] = e
    return resultat


def _officines(acteurs: dict[str, Acteur]) -> list[Acteur]:
    return sorted((a for a in acteurs.values() if a.type == "officine"), key=lambda a: a.id)


def _en_stock(evenements, acteurs, deja: set[str]) -> list[tuple[str, EvenementSimule]]:
    """Unites dont le dernier evenement est une reception par une officine (non dispensees)."""
    return [(s, e) for s, e in sorted(_derniers(evenements).items())
            if s not in deja and e.typeOperation == "reception" and acteurs[e.acteur_id].type == "officine"]


def _completer(injections: list[Injection], n: int, nom: str) -> list[Injection]:
    if len(injections) < n:
        raise ValueError(f"pas assez d'unites candidates pour {nom}: {len(injections)} sur {n}")
    return injections


def injecter_reutilisations(evenements: list[EvenementSimule], acteurs: dict[str, Acteur], n: int,
                            fin: datetime, g: np.random.Generator, deja: set[str]) -> list[Injection]:
    """Une unite deja dispensee est scannee a nouveau (reception) par une officine d'une autre ville."""
    derniers, officines = _derniers(evenements), _officines(acteurs)
    candidats = sorted(s for s, e in derniers.items()
                       if e.typeOperation == "dispensation" and s not in deja)
    resultat: list[Injection] = []
    for indice in g.permutation(len(candidats)):
        if len(resultat) == n:
            break
        serie = candidats[int(indice)]
        dernier = derniers[serie]
        origine = acteurs[dernier.acteur_id]
        autres = [o for o in officines if o.ville != origine.ville]
        if not autres:
            continue
        cible = autres[int(g.integers(len(autres)))]
        quand = _ouvrable(dernier.dateHeure + timedelta(days=float(g.uniform(2, 10))), g)
        if quand > fin:
            continue
        latitude, longitude = _gps(cible, g)
        deja.add(serie)
        resultat.append(Injection(
            "reutilisationIdentifiant", EvenementSimule(serie, "reception", quand, latitude, longitude, cible.id),
            f"unite deja dispensee a {origine.ville}, scannee a nouveau a {cible.ville}"))
    return _completer(resultat, n, "la reutilisation")


def injecter_ruptures(evenements: list[EvenementSimule], acteurs: dict[str, Acteur], n: int,
                      fin: datetime, g: np.random.Generator, deja: set[str]) -> list[Injection]:
    """Une officine dispense une unite qu'elle n'a jamais recue (elle etait destinee a une autre)."""
    officines = _officines(acteurs)
    candidats = _en_stock(evenements, acteurs, deja)
    resultat: list[Injection] = []
    for indice in g.permutation(len(candidats)):
        if len(resultat) == n:
            break
        serie, dernier = candidats[int(indice)]
        autres = [o for o in officines if o.id != dernier.acteur_id]
        cible = autres[int(g.integers(len(autres)))]
        quand = _ouvrable(dernier.dateHeure + timedelta(days=float(g.uniform(1, 10))), g)
        if quand > fin:
            continue
        latitude, longitude = _gps(cible, g)
        deja.add(serie)
        resultat.append(Injection(
            "ruptureSequence", EvenementSimule(serie, "dispensation", quand, latitude, longitude, cible.id),
            f"dispensation a {cible.ville} d'une unite recue par une autre officine ({acteurs[dernier.acteur_id].ville})"))
    return _completer(resultat, n, "la rupture de sequence")


def injecter_trajets(evenements: list[EvenementSimule], acteurs: dict[str, Acteur], n: int,
                     fin: datetime, g: np.random.Generator, deja: set[str]) -> list[Injection]:
    """Une unite est scannee par une officine eloignee (200 km ou plus) moins d'une heure apres."""
    officines = _officines(acteurs)
    candidats = _en_stock(evenements, acteurs, deja)
    resultat: list[Injection] = []
    for indice in g.permutation(len(candidats)):
        if len(resultat) == n:
            break
        serie, dernier = candidats[int(indice)]
        origine = acteurs[dernier.acteur_id]
        loin = [o for o in officines if distance_km(origine.position, o.position) >= DISTANCE_TRAJET_MIN_KM]
        if not loin:
            continue
        cible = loin[int(g.integers(len(loin)))]
        quand = dernier.dateHeure + timedelta(minutes=float(g.uniform(10, 50)))
        if quand > fin:
            continue
        latitude, longitude = _gps(cible, g)
        deja.add(serie)
        resultat.append(Injection(
            "trajetInhabituel", EvenementSimule(serie, "reception", quand, latitude, longitude, cible.id),
            f"unite recue a {origine.ville}, puis a {cible.ville} moins d'une heure plus tard"))
    return _completer(resultat, n, "le trajet inhabituel")