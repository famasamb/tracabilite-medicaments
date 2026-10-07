"""Planche A4 de codes DataMatrix a imprimer pour les vraies photos (phase 3)."""
import cv2
import numpy as np

from app.codes import generer_image_code

LARGEUR, HAUTEUR = 2480, 3508       # A4 a 300 points par pouce
MARGE = 150
COLONNES, LIGNES = 3, 4
PIXELS_PAR_MODULE = 14              # environ 1,2 mm par module a l'impression
ECHELLE_APPLICATION = 8             # echelle utilisee par generer_image_code
POLICE = cv2.FONT_HERSHEY_SIMPLEX


def composer_planche(codes: list[tuple[str, str, str, str]]) -> np.ndarray:
    """Place jusqu'a 12 codes sur une page A4 (image en niveaux de gris).

    Chaque element de `codes` est (numero de serie, contenu du code, nom du produit, lot).
    Chaque case est entouree d'un trait fin a decouper; le numero de serie est ecrit sous le code.
    """
    if len(codes) > COLONNES * LIGNES:
        raise ValueError(f"au plus {COLONNES * LIGNES} codes par planche")
    page = np.full((HAUTEUR, LARGEUR), 255, dtype=np.uint8)
    largeur_case = (LARGEUR - 2 * MARGE) // COLONNES
    hauteur_case = (HAUTEUR - 2 * MARGE) // LIGNES
    for i, (serie, contenu, produit, lot) in enumerate(codes):
        ligne, colonne = divmod(i, COLONNES)
        x0, y0 = MARGE + colonne * largeur_case, MARGE + ligne * hauteur_case
        cv2.rectangle(page, (x0, y0), (x0 + largeur_case, y0 + hauteur_case), 170, 2)

        png = generer_image_code(contenu, ECHELLE_APPLICATION)
        code = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        h, w = code.shape
        code = cv2.resize(code, (w // ECHELLE_APPLICATION * PIXELS_PAR_MODULE,
                                 h // ECHELLE_APPLICATION * PIXELS_PAR_MODULE),
                          interpolation=cv2.INTER_NEAREST)
        h, w = code.shape
        x = x0 + (largeur_case - w) // 2
        y = y0 + 60
        page[y:y + h, x:x + w] = code
        cv2.putText(page, serie, (x0 + 40, y + h + 70), POLICE, 1.1, 0, 2, cv2.LINE_AA)
        cv2.putText(page, f"{produit}  {lot}", (x0 + 40, y + h + 125), POLICE, 0.8, 90, 2, cv2.LINE_AA)
    return page