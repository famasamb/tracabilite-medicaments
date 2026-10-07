"""Test de la page Streamlit du SIG, sans navigateur ni serveur (outil de test de Streamlit)."""
from datetime import date
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from sig.client import ClientAPI  # noqa: E402
from tests.test_tableau import scenario  # noqa: E402

PAGE = str(Path(__file__).resolve().parent.parent / "sig" / "app.py")


def page_connectee(client):
    api = ClientAPI(client)
    profil = api.connecter("pna1", "MotDePasse2026")
    page = AppTest.from_file(PAGE, default_timeout=30)
    page.session_state["client"], page.session_state["profil"] = api, profil
    return page


def test_sans_connexion_la_page_demande_les_identifiants():
    page = AppTest.from_file(PAGE, default_timeout=30).run()
    assert not page.exception
    assert [t.label for t in page.text_input] == ["Adresse de l'API", "Identifiant de connexion", "Mot de passe"]


def test_la_page_affiche_le_tableau_de_bord(client):
    scenario(client)
    page = page_connectee(client).run()
    assert not page.exception
    assert [m.label for m in page.metric] == ["Evenements", "Unites suivies", "Anomalies signalees"]
    assert [m.value for m in page.metric] == ["4", "4", "1"]
    assert any("signaux a verifier" in i.value for i in page.info)


def test_un_filtre_sans_evenement_affiche_le_message(client):
    scenario(client)
    page = page_connectee(client).run()
    page.date_input[0].set_value((date(2030, 1, 1), date(2030, 1, 2))).run()
    assert not page.exception
    assert any("Aucun evenement" in w.value for w in page.warning)
    assert len(page.metric) == 0