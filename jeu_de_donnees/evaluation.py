"""Evaluation d'une methode de lecture sur le jeu de donnees (phase 4 de la methodologie).

Une methode est une fonction qui recoit les octets d'une image (comme l'application) et renvoie le
texte du code lu, ou None. Mesures, pour chaque groupe d'images:
  rappel    = images dont le bon contenu est lu / images du groupe
  precision = lectures correctes / lectures renvoyees (vide si rien n'est lu)
  temps     = duree moyenne d'une lecture, en millisecondes
"""
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.codes import lire_code

Methode = Callable[[bytes], str | None]


@dataclass(frozen=True)
class Resultat:
    fichier: str
    source: str
    degradation: str
    niveau: int
    attendu: str
    lu: str | None
    temps_ms: float

    @property
    def correct(self) -> bool:
        return self.lu == self.attendu


def methode_classique(octets: bytes) -> str | None:
    """Lecture classique: celle que fait deja l'application (zxing sur l'image entiere)."""
    return lire_code(octets)


def evaluer(methode: Methode, lignes: list[dict], dossier_images: Path) -> list[Resultat]:
    """Fait lire chaque image par la methode et mesure le temps de chaque lecture."""
    if lignes:  # un premier appel, non compte, pour ne pas mesurer le chargement des bibliotheques
        methode((dossier_images / lignes[0]["fichier"]).read_bytes())
    resultats = []
    for ligne in lignes:
        octets = (dossier_images / ligne["fichier"]).read_bytes()
        debut = time.perf_counter()
        lu = methode(octets)
        duree = (time.perf_counter() - debut) * 1000
        resultats.append(Resultat(ligne["fichier"], ligne["source"], ligne["degradation"],
                                  int(ligne["niveau"]), ligne["contenuAttendu"], lu, duree))
    return resultats


def synthese(resultats: list[Resultat]) -> list[dict]:
    """Une ligne par (source, degradation, niveau), puis une ligne 'toutes' par source."""
    groupes: dict[tuple, list[Resultat]] = defaultdict(list)
    for r in resultats:
        groupes[(r.source, r.degradation, r.niveau)].append(r)
        groupes[(r.source, "toutes", 0)].append(r)
    lignes = []
    for (source, degradation, niveau), liste in sorted(groupes.items(), key=lambda t: (t[0][0], t[0][1] == "toutes", t[0][1], t[0][2])):
        lues = [r for r in liste if r.lu is not None]
        correctes = [r for r in liste if r.correct]
        lignes.append({
            "source": source, "degradation": degradation, "niveau": niveau, "images": len(liste),
            "lues": len(lues), "correctes": len(correctes),
            "rappel": round(len(correctes) / len(liste), 4),
            "precision": round(len(correctes) / len(lues), 4) if lues else "",
            "tempsMoyenMs": round(sum(r.temps_ms for r in liste) / len(liste), 2)})
    return lignes