"""Tests de l'evaluation des methodes de lecture (phase 4)."""
import cv2
import numpy as np
import pytest

from app.codes import generer_image_code
from jeu_de_donnees.composition import composer_boite
from jeu_de_donnees.degradations import flouter
from jeu_de_donnees.evaluation import evaluer, methode_classique, synthese

CONTENU = "(01)03760000000123(17)280630(10)JD-001(21)ABCDEFGHJKMN"


@pytest.fixture
def jeu(tmp_path):
    """Une image propre, une tres floue, et leur verite terrain."""
    image, _ = composer_boite(generer_image_code(CONTENU), "Produit", "JD-001", np.random.default_rng(1))
    cv2.imwrite(str(tmp_path / "propre.png"), image)
    cv2.imwrite(str(tmp_path / "floue.png"), flouter(image, 12.0))
    base = {"source": "synthetique", "contenuAttendu": CONTENU}
    lignes = [{**base, "fichier": "propre.png", "degradation": "aucune", "niveau": "0"},
              {**base, "fichier": "floue.png", "degradation": "flou", "niveau": "3"}]
    return lignes, tmp_path


def test_la_methode_classique_lit_l_image_propre_et_pas_l_image_tres_floue(jeu):
    lignes, dossier = jeu
    resultats = evaluer(methode_classique, lignes, dossier)
    assert resultats[0].correct and resultats[0].lu == CONTENU
    assert not resultats[1].correct and resultats[1].lu is None
    assert all(r.temps_ms > 0 for r in resultats)


def test_synthese_rappel_precision_et_temps(jeu):
    lignes, dossier = jeu
    par_groupe = {(l["degradation"], l["niveau"]): l for l in synthese(evaluer(methode_classique, lignes, dossier))}
    assert par_groupe[("aucune", 0)]["rappel"] == 1.0 and par_groupe[("aucune", 0)]["precision"] == 1.0
    assert par_groupe[("flou", 3)]["rappel"] == 0.0 and par_groupe[("flou", 3)]["precision"] == ""
    assert par_groupe[("toutes", 0)]["images"] == 2 and par_groupe[("toutes", 0)]["rappel"] == 0.5
    assert par_groupe[("toutes", 0)]["precision"] == 1.0 and par_groupe[("toutes", 0)]["tempsMoyenMs"] > 0


def test_une_lecture_fausse_baisse_la_precision_mais_pas_le_rappel_des_bonnes(jeu):
    lignes, dossier = jeu
    def etourdie(octets: bytes):
        return "(21)FAUX" if len(octets) % 2 == 0 else CONTENU     # une lecture fausse, une juste
    resultats = evaluer(etourdie, lignes, dossier)
    lignes_synthese = {l["degradation"]: l for l in synthese(resultats)}["toutes"]
    assert lignes_synthese["lues"] == 2 and lignes_synthese["correctes"] == sum(r.correct for r in resultats)
    assert lignes_synthese["precision"] == lignes_synthese["correctes"] / 2