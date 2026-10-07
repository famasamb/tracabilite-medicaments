"""Tests de la planche de codes a imprimer pour les vraies photos (phase 3)."""
import pytest
import zxingcpp

from jeu_de_donnees.planche import HAUTEUR, LARGEUR, composer_planche


def code(i):
    serie = f"SERIE{i:07d}"
    return serie, f"(01)03760000000123(17)280630(10)JD-001(21){serie}", "Produit", "JD-001"


def test_tous_les_codes_de_la_planche_sont_lisibles():
    codes = [code(i) for i in range(12)]
    page = composer_planche(codes)
    assert page.shape == (HAUTEUR, LARGEUR)
    assert {r.text for r in zxingcpp.read_barcodes(page)} == {c[1] for c in codes}


def test_une_planche_refuse_plus_de_douze_codes():
    with pytest.raises(ValueError):
        composer_planche([code(i) for i in range(13)])