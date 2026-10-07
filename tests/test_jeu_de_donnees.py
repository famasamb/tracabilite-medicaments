"""Tests du jeu de donnees (phase 3): composition des images et degradations."""
import cv2
import numpy as np

from app.codes import generer_image_code, lire_code
from jeu_de_donnees.composition import HAUTEUR, LARGEUR, composer_boite
from jeu_de_donnees.degradations import flouter, occulter

CONTENU = "(01)03760000000123(17)280630(10)JD-001(21)ABCDEFGHJKMN"


def boite(graine=1):
    return composer_boite(generer_image_code(CONTENU), "Produit", "JD-001", np.random.default_rng(graine))


def test_le_code_reste_lisible_sur_la_boite():
    for graine in range(5):
        image, _ = composer_boite(generer_image_code(CONTENU), "Paracetamol 500 mg", "JD-001",
                                  np.random.default_rng(graine))
        assert image.shape == (HAUTEUR, LARGEUR, 3)
        ok, png = cv2.imencode(".png", image)
        assert lire_code(png.tobytes()) == CONTENU


def test_la_position_annoncee_est_celle_du_code():
    image, (x, y, largeur, hauteur) = boite()
    assert 0 <= x and x + largeur <= LARGEUR and 0 <= y and y + hauteur <= HAUTEUR
    ok, png = cv2.imencode(".png", image[y:y + hauteur, x:x + largeur])
    assert lire_code(png.tobytes()) == CONTENU      # le code est bien dans le cadre annonce


def test_le_flou_adoucit_limage_sans_changer_sa_taille():
    image, _ = boite()
    floue = flouter(image, 4.0)
    nettete = lambda im: cv2.Laplacian(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
    assert floue.shape == image.shape and nettete(floue) < nettete(image)


def test_loclusion_ne_touche_que_le_code_et_couvre_la_part_demandee():
    image, (x, y, largeur, hauteur) = boite()
    resultat = occulter(image, (x, y, largeur, hauteur), 0.10, np.random.default_rng(0))
    modifie = np.any(resultat != image, axis=2)
    assert modifie.any()
    exterieur = modifie.copy()
    exterieur[y:y + hauteur, x:x + largeur] = False
    assert not exterieur.any()                        # rien n'a change hors du code
    part = modifie.sum() / (largeur * hauteur)
    assert 0.07 < part <= 0.10                        # les pixels deja gris ne comptent pas


def test_loclusion_est_reproductible_avec_la_meme_graine():
    image, position = boite()
    a = occulter(image, position, 0.15, np.random.default_rng(5))
    b = occulter(image, position, 0.15, np.random.default_rng(5))
    assert np.array_equal(a, b)