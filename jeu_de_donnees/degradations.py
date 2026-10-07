"""Degradations simulees d'une image de boite (phase 3): flou et occlusion du code."""
import math

import cv2
import numpy as np


def flouter(image: np.ndarray, sigma: float) -> np.ndarray:
    """Flou gaussien sur toute l'image (appareil mal mis au point ou bouge)."""
    return cv2.GaussianBlur(image, (0, 0), sigma)


def occulter(image: np.ndarray, position: tuple[int, int, int, int], fraction: float,
             generateur: np.random.Generator) -> np.ndarray:
    """Cache une partie du code par un rectangle plein (doigt, autocollant, tache).

    `position` = (x, y, largeur, hauteur) du code. Le rectangle a les memes proportions que le
    code et couvre `fraction` de sa surface; il est place au hasard sur le code.
    """
    x, y, largeur, hauteur = position
    cote = math.sqrt(fraction)
    lo, ho = max(1, round(largeur * cote)), max(1, round(hauteur * cote))
    xo = x + int(generateur.integers(0, largeur - lo + 1))
    yo = y + int(generateur.integers(0, hauteur - ho + 1))
    resultat = image.copy()
    cv2.rectangle(resultat, (xo, yo), (xo + lo - 1, yo + ho - 1), (90, 90, 90), -1)
    return resultat