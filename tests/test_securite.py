"""Tests du hachage des mots de passe."""
import pytest

from app.securite import hacher_mot_de_passe, verifier_mot_de_passe


def test_le_bon_mot_de_passe_est_accepte():
    empreinte = hacher_mot_de_passe("MotDePasse2026")
    assert verifier_mot_de_passe("MotDePasse2026", empreinte)


def test_un_mauvais_mot_de_passe_est_refuse():
    empreinte = hacher_mot_de_passe("MotDePasse2026")
    assert not verifier_mot_de_passe("MotDePasse2027", empreinte)


def test_l_empreinte_ne_contient_pas_le_mot_de_passe():
    assert "MotDePasse2026" not in hacher_mot_de_passe("MotDePasse2026")


def test_deux_empreintes_du_meme_mot_de_passe_sont_differentes():
    assert hacher_mot_de_passe("MotDePasse2026") != hacher_mot_de_passe("MotDePasse2026")


def test_mot_de_passe_trop_court_refuse():
    with pytest.raises(ValueError):
        hacher_mot_de_passe("court")


def test_empreinte_illisible_refusee_sans_erreur():
    assert not verifier_mot_de_passe("MotDePasse2026", "n-importe-quoi")