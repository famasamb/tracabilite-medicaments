"""Evaluation sur de vraies photos: rangement, verite terrain, calculs (etape 55)."""
import cv2
import numpy as np
import pytest

from app.codes import generer_image_code
from jeu_de_donnees import evaluer_photos as ep


def contenu(serie):
    return f"(01)03760000000123(17)280630(10)JD-001(21){serie}"


def ranger(racine, condition, nom, serie, flou=0):
    dossier = racine / condition
    dossier.mkdir(parents=True, exist_ok=True)
    octets = generer_image_code(contenu(serie))
    if flou:
        image = cv2.imdecode(np.frombuffer(octets, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        octets = cv2.imencode(".jpg", cv2.GaussianBlur(image, (0, 0), flou))[1].tobytes()
    (dossier / nom).write_bytes(octets)


def test_la_verite_vient_du_nom_du_fichier_et_le_dossier_donne_la_condition(tmp_path):
    ranger(tmp_path, "normal", "AAA111__1.png", "AAA111")
    ranger(tmp_path, "flou", "BBB222__2.png", "BBB222")
    lignes = ep.lister_photos(tmp_path)
    assert [(l["condition"], l["attendu"]) for l in lignes] == [("flou", "BBB222"), ("normal", "AAA111")]


def test_un_fichier_verite_csv_remplace_le_nom(tmp_path):
    ranger(tmp_path, "normal", "IMG_0001.png", "AAA111")
    (tmp_path / "verite.csv").write_text("fichier,attendu\nnormal/IMG_0001.png,AAA111\n", encoding="utf-8")
    assert ep.lister_photos(tmp_path)[0]["attendu"] == "AAA111"


def test_evaluation_et_synthese(tmp_path):
    ranger(tmp_path, "normal", "AAA111__1.png", "AAA111")
    ranger(tmp_path, "normal", "BBB222__1.png", "BBB222")
    ranger(tmp_path, "normal", "CCC333__1.png", "ZZZ999")      # le code photographie n'est pas celui annonce
    resultats = ep.evaluer_dossier(tmp_path, localiseur=None)
    assert [r["ok_classique"] for r in resultats] == [1, 1, 0]
    resume = {(l["condition"], l["methode"]): l for l in ep.synthetiser(resultats)}
    cl = resume[("normal", "classique")]
    assert (cl["photos"], cl["lues"], cl["correctes"], cl["fausses"]) == (3, 3, 2, 1)
    assert cl["rappel"] == pytest.approx(0.6667, abs=1e-4) and cl["precision"] == pytest.approx(0.6667, abs=1e-4)
    assert ("toutes", "hybride") in resume


def test_une_photo_illisible_compte_comme_non_lue(tmp_path):
    (tmp_path / "flou").mkdir()
    cv2.imwrite(str(tmp_path / "flou" / "AAA111__1.png"), np.full((200, 200), 128, np.uint8))
    r = ep.evaluer_dossier(tmp_path, None)[0]
    assert r["lu_classique"] == "" and r["ok_classique"] == 0
