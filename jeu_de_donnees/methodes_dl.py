"""Methodes de lecture deep learning et hybride (phase 4 de la methodologie).

  deep learning = YOLOv8 localise le code sur l'image, puis la zone recadree est lue par zxing.
                  Le modele ne decode pas: la lecture reste algorithmique (zxing), le deep learning
                  sert a retrouver ou est le code.
  hybride       = lecture classique d'abord; si elle echoue, la methode deep learning prend le relais
                  (c'est l'ordre du parcours des fiches 7 et 8: classique, puis deep learning).
"""
from pathlib import Path
from typing import Callable

from app.lecture import (Boite, CONFIANCE_MIN, Localiseur, MARGE, MODELE, TAILLE_YOLO,  # noqa: F401
                         lire_zone, localiseur_yolo, recadrer)

from .evaluation import Methode


def methode_deep_learning(localiseur: Localiseur, marge: float = MARGE) -> Methode:
    return lambda octets: lire_zone(octets, localiseur, marge)


def methode_hybride(classique: Methode, deep_learning: Methode) -> Methode:
    def lire(octets: bytes) -> str | None:
        lu = classique(octets)
        return lu if lu is not None else deep_learning(octets)
    return lire
