"""Tests de la composition des images du jeu de donnees (phase 3)."""
import cv2
import numpy as np

from app.codes import generer_image_code, lire_code
from jeu_de_donnees.composition import HAUTEUR, LARGEUR, composer_boite

CONTENU = "(01)03760000000123(17)280630(10)JD-001(21)ABCDEFGHJKMN"


def test_le_code_reste_lisible_sur_la_boite():
    for graine in range(5):
        image, _ = composer_boite(generer_image_code(CONTENU), "Paracetamol 500 mg", "JD-001",
                                  np.random.default_rng(graine))
        assert image.shape == (HAUTEUR, LARGEUR, 3)
        ok, png = cv2.imencode(".png", image)
        assert lire_code(png.tobytes()) == CONTENU


def test_la_position_annoncee_est_celle_du_code():
    image, (x, y, largeur, hauteur) = composer_boite(generer_image_code(CONTENU), "Produit", "JD-001",
                                                     np.random.default_rng(1))
    assert 0 <= x and x + largeur <= LARGEUR and 0 <= y and y + hauteur <= HAUTEUR
    ok, png = cv2.imencode(".png", image[y:y + hauteur, x:x + largeur])
    assert lire_code(png.tobytes()) == CONTENU      # le code est bien dans le cadre annonce