"""Lecture du code sur une photo: methode classique, puis deep learning si elle echoue (fiches 7 et 8).

  classique     = zxing lit directement l'image (rapide).
  deep learning = YOLOv8 localise le code sur l'image, la zone recadree est lue par zxing.
                  Le modele ne decode pas: il retrouve OU est le code; la lecture reste algorithmique.
  hybride       = classique d'abord; si elle echoue, deep learning (methode evaluee a l'etape 36).

YOLO est facultatif: sans ultralytics ou sans le fichier du modele, l'application lit en mode classique seul.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import zxingcpp

from .codes import lire_code

journal = logging.getLogger("tracabilite.lecture")

Boite = tuple[int, int, int, int]                  # x, y, largeur, hauteur, en pixels
Localiseur = Callable[[np.ndarray], Boite | None]  # image couleur (BGR) -> boite du code, ou None

MARGE = 0.25           # part de la taille de la boite ajoutee de chaque cote (choisie sur le groupe val: 0, 0.10, 0.25, 0.50 compares)
CONFIANCE_MIN = 0.25   # en dessous, une detection de YOLO est ignoree (valeur par defaut d'ultralytics)
TAILLE_YOLO = 640      # meme taille que pendant l'entrainement
MODELE = Path(os.getenv("MODELE_YOLO") or Path(__file__).resolve().parent.parent / "jeu_de_donnees" / "modeles" / "datamatrix" / "weights" / "best.pt")

CLASSIQUE, DEEP_LEARNING = "classique", "deep_learning"


@dataclass
class Lecture:
    texte: str | None
    methode: str | None      # "classique", "deep_learning", ou None si rien n'a ete lu


def recadrer(image: np.ndarray, boite: Boite, marge: float = MARGE) -> np.ndarray:
    """Decoupe la boite avec une marge, sans sortir de l'image."""
    x, y, largeur, hauteur = boite
    dx, dy = int(round(largeur * marge)), int(round(hauteur * marge))
    haut, bas = max(0, y - dy), min(image.shape[0], y + hauteur + dy)
    gauche, droite = max(0, x - dx), min(image.shape[1], x + largeur + dx)
    return image[haut:bas, gauche:droite]


def lire_zone(octets: bytes, localiseur: Localiseur, marge: float = MARGE) -> str | None:
    """Methode deep learning: le localiseur trouve le code, la zone recadree est lue par zxing."""
    image = cv2.imdecode(np.frombuffer(octets, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return None
    boite = localiseur(image)
    if boite is None:
        return None
    zone = cv2.cvtColor(recadrer(image, boite, marge), cv2.COLOR_BGR2GRAY)
    if zone.size == 0:
        return None
    resultats = zxingcpp.read_barcodes(zone)
    return resultats[0].text if resultats else None


def localiseur_yolo(chemin_modele: Path = MODELE, confiance_min: float = CONFIANCE_MIN,
                    appareil: str = "cpu") -> Localiseur:
    """Charge le modele entraine (etape 35); garde la detection la plus sure de chaque image."""
    from ultralytics import YOLO   # import ici: l'application n'a pas besoin d'ultralytics pour demarrer
    modele = YOLO(str(chemin_modele))

    def localiser(image: np.ndarray) -> Boite | None:
        resultat = modele.predict(image, imgsz=TAILLE_YOLO, conf=confiance_min, device=appareil, verbose=False)[0]
        if len(resultat.boxes) == 0:
            return None
        meilleur = int(resultat.boxes.conf.argmax())
        x1, y1, x2, y2 = resultat.boxes.xyxy[meilleur].tolist()
        x1, y1, x2, y2 = int(np.floor(x1)), int(np.floor(y1)), int(np.ceil(x2)), int(np.ceil(y2))
        return (x1, y1, x2 - x1, y2 - y1)
    return localiser


_localiseur: Localiseur | None = None
_essaye = False


def localiseur_disponible() -> Localiseur | None:
    """Charge YOLO une seule fois; renvoie None (et le dit dans le journal) s'il est indisponible."""
    global _localiseur, _essaye
    if not _essaye:
        _essaye = True
        if not MODELE.is_file():
            journal.warning("Modele YOLO absent (%s): lecture classique seule.", MODELE)
        else:
            try:
                _localiseur = localiseur_yolo()
            except Exception as erreur:  # noqa: BLE001 - ultralytics absent ou modele illisible
                journal.warning("YOLO indisponible (%s): lecture classique seule.", erreur)
    return _localiseur


def lire_hybride(octets: bytes, localiseur: Localiseur | None = None) -> Lecture:
    """Classique d'abord, puis deep learning si le classique ne lit rien."""
    texte = lire_code(octets)
    if texte is not None:
        return Lecture(texte, CLASSIQUE)
    localiseur = localiseur or localiseur_disponible()
    if localiseur is None:
        return Lecture(None, None)
    texte = lire_zone(octets, localiseur)
    return Lecture(texte, DEEP_LEARNING if texte is not None else None)
