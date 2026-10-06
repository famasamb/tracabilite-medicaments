"""Tests du cas Enregistrer la reception / l'expedition (fiche 7)."""
import io
import zipfile
from datetime import date, timedelta

from app.codes import generer_image_code
from app.db import get_db
from app.main import app as application
from app.models import Anomalie, Evenement, StatutUnite, Unite
from tests.test_auth import inscrire, se_connecter

PRODUIT = {"nom": "Paracetamol 500 mg", "composition": "Paracetamol 500 mg",
           "formePharmaceutique": "Comprime", "conditionnement": "Boite de 16",
           "gtin": "03760000000123"}


def connecte(client, identifiant, mdp="MotDePasse2026"):
    jeton = se_connecter(client, identifiant, mdp).json()["access_token"]
    return {"Authorization": f"Bearer {jeton}"}


def inscrire_structure(client, type_, reference, identifiant):
    r = client.post("/structures/inscription", json={
        "structure": {"nom": f"Structure {identifiant}", "type": type_, "localisation": "Dakar",
                      "referenceAutorisation": reference},
        "responsable": {"nom": "Responsable Test", "fonction": "Responsable",
                        "identifiantConnexion": identifiant, "motDePasse": "MotDePasse2026"}})
    assert r.status_code == 201
    return connecte(client, identifiant)


def serialiser(client, quantite=3):
    """Un fabricant serialise un lot; renvoie ({numero_serie: image_png}, en-tetes du fabricant)."""
    inscrire(client)
    entete = connecte(client, "awa.diop")
    pid = client.post("/produits", json=PRODUIT, headers=entete).json()["id"]
    r = client.post("/lots/serialisation", headers=entete, json={
        "produit_id": pid, "numeroLot": "LOT2026A", "quantite": quantite,
        "datePeremption": (date.today() + timedelta(days=400)).isoformat()})
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    return {n[:-4]: zf.read(n) for n in zf.namelist()}, entete


def session(client):
    return next(application.dependency_overrides[get_db]())


def test_expedition_par_image_du_code(client):
    images, fabricant = serialiser(client)
    serie, png = next(iter(images.items()))
    r = client.post("/evenements", headers=fabricant, data={"typeOperation": "expedition",
                    "latitude": "14.6928", "longitude": "-17.4467"},
                    files={"image": ("code.png", png, "image/png")})
    assert r.status_code == 201
    corps = r.json()
    assert corps["numeroSerie"] == serie and corps["typeOperation"] == "expedition"
    assert corps["latitude"] == 14.6928 and corps["alerte"] is False
    e = session(client).query(Evenement).one()
    assert e.numeroSerie == serie and e.utilisateur_id


def test_la_lecture_du_code_passe_avant_la_saisie_manuelle(client):
    images, fabricant = serialiser(client)
    serie, png = next(iter(images.items()))
    r = client.post("/evenements", headers=fabricant,
                    data={"typeOperation": "expedition", "numeroSerie": "string"},
                    files={"image": ("code.png", png, "image/png")})
    assert r.status_code == 201 and r.json()["numeroSerie"] == serie


def test_image_illisible_avec_saisie_manuelle_utilise_la_saisie(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    r = client.post("/evenements", headers=fabricant,
                    data={"typeOperation": "expedition", "numeroSerie": serie},
                    files={"image": ("flou.png", b"image floue", "image/png")})
    assert r.status_code == 201 and r.json()["numeroSerie"] == serie
    
    
def test_reception_par_saisie_manuelle(client):
    images, _ = serialiser(client)
    serie = next(iter(images))
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    r = client.post("/evenements", headers=officine,
                    data={"typeOperation": "reception", "numeroSerie": serie})
    assert r.status_code == 201 and r.json()["latitude"] is None


def test_code_illisible_demande_la_saisie_manuelle(client):
    _, fabricant = serialiser(client)
    r = client.post("/evenements", headers=fabricant, data={"typeOperation": "expedition"},
                    files={"image": ("code.png", b"ceci n'est pas une image", "image/png")})
    assert r.status_code == 422 and "Code illisible" in r.json()["detail"]
    assert session(client).query(Evenement).count() == 0


def test_ni_image_ni_numero_refuse(client):
    _, fabricant = serialiser(client)
    r = client.post("/evenements", headers=fabricant, data={"typeOperation": "expedition"})
    assert r.status_code == 422


def test_identifiant_inconnu_refuse(client):
    _, fabricant = serialiser(client)
    r = client.post("/evenements", headers=fabricant,
                    data={"typeOperation": "expedition", "numeroSerie": "INCONNU12345"})
    assert r.status_code == 404


def test_code_gs1_valide_mais_unite_inexistante_refuse(client):
    _, fabricant = serialiser(client)
    png = generer_image_code("(01)03760000000123(17)280630(10)LOT9(21)ZZZZZZZZZZZZ")
    r = client.post("/evenements", headers=fabricant, data={"typeOperation": "expedition"},
                    files={"image": ("code.png", png, "image/png")})
    assert r.status_code == 404


def test_unite_desactivee_enregistree_avec_alerte(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    db = session(client)
    db.get(Unite, serie).statut = StatutUnite.desactivee
    db.commit()
    r = client.post("/evenements", headers=fabricant,
                    data={"typeOperation": "expedition", "numeroSerie": serie})
    assert r.status_code == 201 and r.json()["alerte"] is True
    anomalie = db.query(Anomalie).one()
    assert anomalie.typeAnomalie.value == "reutilisationIdentifiant" and anomalie.statut == "a_verifier"


def test_droits_selon_la_structure(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    donnees = lambda op: {"typeOperation": op, "numeroSerie": serie}
    # le fabricant expedie seulement
    assert client.post("/evenements", headers=fabricant, data=donnees("reception")).status_code == 403
    # l'officine recoit seulement
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    assert client.post("/evenements", headers=officine, data=donnees("expedition")).status_code == 403
    assert client.post("/evenements", headers=officine, data=donnees("reception")).status_code == 201
    # le grossiste fait les deux
    grossiste = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    assert client.post("/evenements", headers=grossiste, data=donnees("reception")).status_code == 201
    assert client.post("/evenements", headers=grossiste, data=donnees("expedition")).status_code == 201


def test_la_dispensation_nest_pas_geree_ici(client):
    images, fabricant = serialiser(client)
    r = client.post("/evenements", headers=fabricant,
                    data={"typeOperation": "dispensation", "numeroSerie": next(iter(images))})
    assert r.status_code == 422


def test_position_incomplete_ou_hors_limites_refusee(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    base = {"typeOperation": "expedition", "numeroSerie": serie}
    assert client.post("/evenements", headers=fabricant, data=dict(base, latitude="14.6")).status_code == 422
    assert client.post("/evenements", headers=fabricant,
                       data=dict(base, latitude="95", longitude="10")).status_code == 422


def test_sans_connexion_refuse(client):
    r = client.post("/evenements", data={"typeOperation": "expedition", "numeroSerie": "X"})
    assert r.status_code == 401