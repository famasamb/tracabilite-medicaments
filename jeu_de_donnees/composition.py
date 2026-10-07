"""Composition d'une image de boite portant un code DataMatrix (jeu de donnees, phase 3)."""
import cv2
import numpy as np

LARGEUR, HAUTEUR = 800, 600
CARTON = (150, 185, 210)      # couleur carton (BGR)
ETIQUETTE = (245, 245, 245)   # etiquette claire collee sur la boite
POLICE = cv2.FONT_HERSHEY_SIMPLEX


def composer_boite(png_code: bytes, produit: str, lot: str, generateur: np.random.Generator):
    """Pose le code (PNG produit par l'application) sur une etiquette de boite.

    Renvoie l'image (BGR) et la position du code (x, y, largeur, hauteur) en pixels.
    La taille et la position du code varient d'une image a l'autre.
    """
    code = cv2.imdecode(np.frombuffer(png_code, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if code is None:
        raise ValueError("image de code illisible")
    h0, w0 = code.shape
    largeur = int(generateur.integers(200, 321))
    hauteur = max(1, round(largeur * h0 / w0))   # un DataMatrix peut etre rectangulaire
    code = cv2.resize(code, (largeur, hauteur), interpolation=cv2.INTER_NEAREST)

    image = np.full((HAUTEUR, LARGEUR, 3), CARTON, dtype=np.uint8)
    cv2.rectangle(image, (40, 40), (LARGEUR - 40, HAUTEUR - 40), ETIQUETTE, -1)
    cv2.putText(image, produit, (70, 100), POLICE, 0.9, (30, 30, 30), 2, cv2.LINE_AA)
    cv2.putText(image, f"Lot {lot}", (70, 140), POLICE, 0.7, (60, 60, 60), 2, cv2.LINE_AA)

    x = int(generateur.integers(60, LARGEUR - 60 - largeur + 1))
    y = int(generateur.integers(170, HAUTEUR - 60 - hauteur + 1))
    image[y:y + hauteur, x:x + largeur] = cv2.cvtColor(code, cv2.COLOR_GRAY2BGR)
    return image, (x, y, largeur, hauteur)