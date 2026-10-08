"""Tests des numeros de serie et des codes 2D."""
from datetime import date

import pytest

from app.codes import (ALPHABET, LONGUEUR_SERIE, cle_de_controle_gtin, construire_contenu,
                       generer_image_code, generer_numeros_serie, gtin_valide, lire_code)

GTIN = "0340093000012" + str(cle_de_controle_gtin("0340093000012"))  # GTIN-14 valide


def test_numeros_de_serie_uniques_et_bien_formes():
    series = generer_numeros_serie(10000)
    assert len(series) == len(set(series)) == 10000
    assert all(len(s) == LONGUEUR_SERIE and set(s) <= set(ALPHABET) for s in series)


def test_numeros_deja_pris_jamais_repris():
    pris = set(generer_numeros_serie(500))
    nouveaux = generer_numeros_serie(500, deja_pris=pris)
    assert pris.isdisjoint(nouveaux)


def test_quantite_nulle_refusee():
    with pytest.raises(ValueError):
        generer_numeros_serie(0)


def test_cle_de_controle_gtin():
    assert gtin_valide(GTIN)
    faux = GTIN[:-1] + str((int(GTIN[-1]) + 1) % 10)
    assert not gtin_valide(faux)
    assert not gtin_valide("123")


def test_contenu_avec_gtin():
    c = construire_contenu(GTIN, "idprod", "LOT123", date(2028, 9, 30), "AB3KX9M2QW7P")
    assert c == f"(01){GTIN}(17)280930(10)LOT123(21)AB3KX9M2QW7P"


def test_contenu_sans_gtin_utilise_l_identifiant_interne():
    c = construire_contenu(None, "idprod", "LOT123", date(2028, 9, 30), "AB3KX9M2QW7P")
    assert c == "(17)280930(10)LOT123(21)AB3KX9M2QW7P(91)idprod"


def test_gtin_invalide_refuse():
    with pytest.raises(ValueError):
        construire_contenu("12345678901234", "idprod", "LOT1", date(2028, 1, 1), "S1")


def test_lot_invalide_refuse():
    with pytest.raises(ValueError):
        construire_contenu(GTIN, "idprod", "", date(2028, 1, 1), "S1")


def test_le_code_genere_se_relit_avec_gtin():
    contenu = construire_contenu(GTIN, "idprod", "LOT123", date(2028, 9, 30), "AB3KX9M2QW7P")
    assert lire_code(generer_image_code(contenu)) == contenu


def test_le_code_genere_se_relit_sans_gtin():
    contenu = construire_contenu(None, "a1b2c3d4e5f6", "LOT-9", date(2027, 3, 1), "ZK7Q2M9XW3RT")
    assert lire_code(generer_image_code(contenu)) == contenu


def test_image_sans_code_renvoie_none():
    import numpy as np, cv2
    ok, png = cv2.imencode(".png", np.full((100, 100), 255, dtype=np.uint8))
    assert lire_code(png.tobytes()) is None


def test_le_texte_sous_le_code_ne_gene_pas_la_lecture_et_porte_le_numero_de_serie():
    contenu = construire_contenu("03400930000021", "p1", "LOT-001", date(2030, 12, 31), "ABC123DEF456")
    sans, avec = generer_image_code(contenu), generer_image_code(contenu, avec_texte=True)
    assert lire_code(avec) == contenu
    assert len(avec) > len(sans)  # la marge de texte ajoute des lignes a l'image
    from app.codes import _lignes_lisibles
    assert _lignes_lisibles(contenu) == ["(01)03400930000021", "(17)301231", "(10)LOT-001", "(21)ABC123DEF456"]
