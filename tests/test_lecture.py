"""Lecture hybride dans l'application: classique d'abord, deep learning en secours (fiches 7 et 8)."""
import cv2
import numpy as np

from app import lecture
from app.codes import generer_image_code, lire_code
from app.lecture import CLASSIQUE, DEEP_LEARNING, Lecture, lire_hybride, lire_zone
from jeu_de_donnees.composition import composer_boite
from jeu_de_donnees.degradations import flouter
from tests.test_evenements import serialiser

CONTENU = "(01)03760000000123(17)280630(10)JD-001(21)ABCDEFGHJKMN"


def scene_floue(contenu=CONTENU):
    """Photo d'une boite dont le code est trop flou pour la lecture classique mais encore lisible une fois localise.

    Renvoie (octets de l'image, boite du code). On cherche parmi quelques tirages reproductibles.
    """
    for graine in range(1, 60):
        for sigma in (3, 4, 5, 6, 7, 8, 9):
            image, boite = composer_boite(generer_image_code(contenu), "Produit", "JD-001", np.random.default_rng(graine))
            octets = cv2.imencode(".png", flouter(image, sigma))[1].tobytes()
            if lire_code(octets) is None and lire_zone(octets, lambda img: boite) == contenu:
                return octets, boite
    raise AssertionError("aucune scene floue adaptee trouvee")


def test_un_code_net_est_lu_en_classique_sans_appeler_le_deep_learning():
    appels = []
    octets = generer_image_code(CONTENU)
    lu = lire_hybride(octets, localiseur=lambda image: appels.append(1))
    assert lu == Lecture(CONTENU, CLASSIQUE) and appels == []


def test_un_code_flou_est_retrouve_par_le_deep_learning():
    octets, boite = scene_floue()
    assert lire_code(octets) is None                                    # le classique echoue
    assert lire_hybride(octets, localiseur=lambda image: boite) == Lecture(CONTENU, DEEP_LEARNING)


def test_sans_modele_disponible_la_lecture_reste_classique(monkeypatch):
    monkeypatch.setattr(lecture, "localiseur_disponible", lambda: None)
    octets, _ = scene_floue()
    assert lire_hybride(octets) == Lecture(None, None)


def test_un_localiseur_qui_ne_trouve_rien_ne_lit_rien():
    octets, _ = scene_floue()
    assert lire_hybride(octets, localiseur=lambda image: None) == Lecture(None, None)


def test_le_modele_absent_ou_ultralytics_manquant_ne_fait_pas_planter(monkeypatch, tmp_path):
    monkeypatch.setattr(lecture, "MODELE", tmp_path / "inexistant.pt")
    monkeypatch.setattr(lecture, "_localiseur", None)
    monkeypatch.setattr(lecture, "_essaye", False)
    assert lecture.localiseur_disponible() is None


def test_la_route_indique_comment_le_code_a_ete_lu(client, monkeypatch):
    images, fabricant = serialiser(client)
    serie, png = next(iter(images.items()))
    # 1. code net: classique
    r = client.post("/unites/statut", headers=fabricant, files={"image": ("code.png", png, "image/png")})
    assert r.json()["methodeLecture"] == "classique"
    # 2. saisie manuelle
    r = client.post("/unites/statut", headers=fabricant, data={"numeroSerie": serie})
    assert r.json()["methodeLecture"] == "saisie"
    # 3. photo floue retrouvee par le deep learning (localiseur simule avec la vraie boite)
    octets, boite = scene_floue(lire_code(png))
    monkeypatch.setattr(lecture, "localiseur_disponible", lambda: (lambda image: boite))
    r = client.post("/unites/statut", headers=fabricant, files={"image": ("photo.png", octets, "image/png")})
    assert r.status_code == 200 and r.json()["methodeLecture"] == "deep_learning" and r.json()["numeroSerie"] == serie
    # 4. photo floue sans modele: illisible, il faut saisir
    monkeypatch.setattr(lecture, "localiseur_disponible", lambda: None)
    r = client.post("/unites/statut", headers=fabricant, files={"image": ("photo.png", octets, "image/png")})
    assert r.status_code == 422 and "illisible" in r.json()["detail"].lower()
