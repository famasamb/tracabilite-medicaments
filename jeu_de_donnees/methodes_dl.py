"""Methodes de lecture deep learning et hybride (phase 4 de la methodologie).

  deep learning = YOLOv8 localise le code sur l'image, puis la zone recadree est lue par zxing.
                  Le modele ne decode pas: la lecture reste algorithmique (zxing), le deep learning
                  sert a retrouver ou est le code.
  hybride       = lecture classique d'abord; si elle echoue, la methode deep learning prend le relais
                  (c'est l'ordre du parcours des fiches 7 et 8: classique, puis deep learning).
"""
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import zxingcpp

from .evaluation import Methode

Boite = tuple[int, int, int, int]                  # x, y, largeur, hauteur, en pixels
Localiseur = Callable[[np.ndarray], Boite | None]  # image couleur (BGR) -> boite du code, ou None

MARGE = 0.25           # part de la taille de la boite ajoutee de chaque cote (choisie sur le groupe val: 0, 0.10, 0.25, 0.50 compares)
CONFIANCE_MIN = 0.25   # en dessous, une detection de YOLO est ignoree (valeur par defaut d'ultralytics)
TAILLE_YOLO = 640      # meme taille que pendant l'entrainement
MODELE = Path(__file__).parent / "modeles" / "datamatrix" / "weights" / "best.pt"


def recadrer(image: np.ndarray, boite: Boite, marge: float = MARGE) -> np.ndarray:
    """Decoupe la boite avec une marge, sans sortir de l'image."""
    x, y, largeur, hauteur = boite
    dx, dy = int(round(largeur * marge)), int(round(hauteur * marge))
    haut, bas = max(0, y - dy), min(image.shape[0], y + hauteur + dy)
    gauche, droite = max(0, x - dx), min(image.shape[1], x + largeur + dx)
    return image[haut:bas, gauche:droite]


def methode_deep_learning(localiseur: Localiseur, marge: float = MARGE) -> Methode:
    def lire(octets: bytes) -> str | None:
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
    return lire


def methode_hybride(classique: Methode, deep_learning: Methode) -> Methode:
    def lire(octets: bytes) -> str | None:
        lu = classique(octets)
        return lu if lu is not None else deep_learning(octets)
    return lire


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