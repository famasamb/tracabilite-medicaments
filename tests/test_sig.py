"""Tests de l'application SIG: client de l'API et carte (la page Streamlit elle-meme est testee a part)."""
from datetime import date

import pytest

pytest.importorskip("folium")
from sig.carte import CENTRE_SENEGAL, construire_carte, html_de_la_carte  # noqa: E402
from sig.client import ClientAPI, ErreurAPI  # noqa: E402
from tests.test_tableau import scenario  # noqa: E402


def client_api(client):
    """Un ClientAPI branche sur l'application de test, sans serveur."""
    return ClientAPI(client)


def test_connexion_d_un_utilisateur_de_la_pna(client):
    scenario(client)
    profil = client_api(client).connecter("pna1", "MotDePasse2026")
    assert profil["structure_type"] == "PNA"


def test_mauvais_mot_de_passe_ou_compte_inconnu(client):
    scenario(client)
    with pytest.raises(ErreurAPI, match="incorrect") as e:
        client_api(client).connecter("pna1", "faux")
    assert e.value.statut == 401
    with pytest.raises(ErreurAPI, match="Aucun compte"):
        client_api(client).connecter("inconnu", "x")


def test_un_compte_hors_pna_est_refuse(client):
    scenario(client)
    api = client_api(client)
    with pytest.raises(ErreurAPI, match="reservee aux utilisateurs de la PNA"):
        api.connecter("pharma1", "MotDePasse2026")
    assert "Authorization" not in client.headers          # la session n'est pas gardee


def test_liste_des_sr_et_tableau_de_bord(client):
    scenario(client)
    api = client_api(client)
    api.connecter("pna1", "MotDePasse2026")
    sr = {s["nom"]: s["id"] for s in api.liste_sr()}
    assert {"SR Dakar", "SR Diourbel"} <= set(sr)
    tout = api.tableau()
    assert tout["nombreEvenements"] == 4 and tout["anomaliesSignalees"] == 1
    diourbel = api.tableau(sr["SR Diourbel"])
    assert diourbel["nombreEvenements"] == 2
    vide = api.tableau(du=date(2030, 1, 1))
    assert vide["nombreEvenements"] == 0 and "Aucun evenement" in vide["message"]


def test_les_erreurs_de_l_api_deviennent_des_messages_lisibles(client):
    scenario(client)
    api = client_api(client)
    api.connecter("pna1", "MotDePasse2026")
    with pytest.raises(ErreurAPI, match="precede") as e:
        api.tableau(du=date(2026, 12, 31), au=date(2026, 1, 1))
    assert e.value.statut == 422
    with pytest.raises(ErreurAPI, match="introuvable"):
        api.tableau("inexistant")


def test_sans_connexion_l_acces_est_refuse(client):
    scenario(client)
    with pytest.raises(ErreurAPI) as e:
        client_api(client).tableau()
    assert e.value.statut == 401


def test_adresse_injoignable_donne_un_message_clair():
    with pytest.raises(ErreurAPI, match="Impossible de joindre"):
        ClientAPI.vers("http://127.0.0.1:9").connecter("x", "y")


def test_la_carte_a_un_cercle_par_point():
    points = [{"latitude": 14.69, "longitude": -17.44, "typeOperation": "reception",
               "dateHeure": "2026-10-01T09:00:00", "sr": "SR Dakar"},
              {"latitude": 14.65, "longitude": -16.23, "typeOperation": "expedition",
               "dateHeure": "2026-10-01T10:00:00", "sr": "SR Diourbel"}]
    html = construire_carte(points)._repr_html_()
    assert html.count("L.circleMarker(") == 2 and "SR Diourbel" in html


def test_la_carte_sans_point_montre_le_senegal():
    carte = construire_carte([])
    assert tuple(carte.location) == CENTRE_SENEGAL
    assert "L.circleMarker(" not in carte._repr_html_()


def test_le_html_de_la_carte_est_une_page_complete_et_pas_la_version_notebook():
    point = {"latitude": 14.69, "longitude": -17.44, "typeOperation": "reception",
             "dateHeure": "2026-10-01T09:00:00", "sr": "SR Dakar"}
    html = html_de_la_carte([point])
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "L.circleMarker(" in html and "Trust Notebook" not in html