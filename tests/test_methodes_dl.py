"""Tests des methodes deep learning et hybride (phase 4)."""
import cv2
import numpy as np
import pytest

from app.codes import generer_image_code
from jeu_de_donnees.composition import composer_boite
from jeu_de_donnees.degradations import flouter
from jeu_de_donnees.evaluation import methode_classique
from jeu_de_donnees.methodes_dl import MODELE, localiseur_yolo, methode_deep_learning, methode_hybride, recadrer

CONTENU = "(01)03760000000123(17)280630(10)JD-001(21)ABCDEFGHJKMN"


def image_et_boite(graine=1, flou=None):
    image, boite = composer_boite(generer_image_code(CONTENU), "Produit", "JD-001", np.random.default_rng(graine))
    if flou:
        image = flouter(image, flou)
    return image, boite


def en_png(image) -> bytes:
    return cv2.imencode(".png", image)[1].tobytes()


def test_recadrer_ajoute_une_marge_sans_sortir_de_l_image():
    image = np.zeros((100, 200), np.uint8)
    assert recadrer(image, (50, 40, 20, 10), marge=0.5).shape == (20, 40)
    assert recadrer(image, (0, 0, 20, 10), marge=0.5).shape == (15, 30)        # coupe aux bords haut et gauche
    assert recadrer(image, (190, 95, 20, 10), marge=0.5).shape == (10, 20)     # coupe aux bords bas et droit


def test_la_lecture_deep_learning_depend_de_la_boite_trouvee():
    image, boite = image_et_boite()
    octets = en_png(image)
    assert methode_deep_learning(lambda img: boite)(octets) == CONTENU           # bonne boite: le code est lu
    assert methode_deep_learning(lambda img: None)(octets) is None               # rien trouve: pas de lecture
    assert methode_deep_learning(lambda img: (5, 5, 40, 40))(octets) is None     # mauvaise zone: pas de lecture
    assert methode_deep_learning(lambda img: boite)(b"pas une image") is None


def test_la_methode_hybride_essaie_le_classique_puis_le_deep_learning():
    appels = []
    def classique_ok(o): appels.append("classique"); return "A"
    def classique_ko(o): appels.append("classique"); return None
    def dl_ok(o): appels.append("dl"); return "B"
    def dl_ko(o): appels.append("dl"); return None
    assert methode_hybride(classique_ok, dl_ok)(b"x") == "A" and appels == ["classique"]
    appels.clear()
    assert methode_hybride(classique_ko, dl_ok)(b"x") == "B" and appels == ["classique", "dl"]
    appels.clear()
    assert methode_hybride(classique_ko, dl_ko)(b"x") is None and appels == ["classique", "dl"]


@pytest.mark.skipif(not MODELE.exists(), reason="modele YOLO absent (etape 35)")
def test_le_modele_yolo_entraine_retrouve_le_code_et_le_hybride_le_lit():
    pytest.importorskip("ultralytics")
    localiser = localiseur_yolo()
    for graine in (1, 2, 3):
        image, (x, y, l, h) = image_et_boite(graine)
        trouve = localiser(image)
        assert trouve is not None
        tx, ty, tl, th = trouve
        dedans = max(0, min(x + l, tx + tl) - max(x, tx)) * max(0, min(y + h, ty + th) - max(y, ty))
        assert dedans / (l * h + tl * th - dedans) > 0.5          # recouvrement avec le vrai code (IoU)
    lecture = methode_hybride(methode_classique, methode_deep_learning(localiser))
    assert lecture(en_png(image_et_boite(4)[0])) == CONTENU