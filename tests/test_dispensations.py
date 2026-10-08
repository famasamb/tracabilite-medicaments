"""Tests du cas Enregistrer la dispensation (fiche 8)."""
from app.models import Anomalie, Evenement, ReferenceAutorisation, StatutUnite, TypeStructure, Unite
from tests.test_evenements import connecte, inscrire_structure, serialiser, session


def preparer(client):
    """Une officine qui a recu une unite serialisee. Renvoie (serie, image, en-tetes officine)."""
    images, _ = serialiser(client)
    serie, png = next(iter(images.items()))
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    r = client.post("/evenements", headers=officine,
                    data={"typeOperation": "reception", "numeroSerie": serie})
    assert r.status_code == 201
    return serie, png, officine


def test_dispensation_nominale_par_image_desactive_lunite(client):
    serie, png, officine = preparer(client)
    r = client.post("/dispensations", headers=officine,
                    data={"latitude": "14.6928", "longitude": "-17.4467"},
                    files={"image": ("code.png", png, "image/png")})
    assert r.status_code == 201
    corps = r.json()
    assert corps["numeroSerie"] == serie and corps["typeOperation"] == "dispensation"
    assert corps["alerte"] is False
    db = session(client)
    assert db.get(Unite, serie).statut == StatutUnite.desactivee
    assert db.query(Evenement).count() == 2  # reception + dispensation
    assert db.query(Anomalie).count() == 0


def test_dispensation_par_saisie_manuelle(client):
    serie, _, officine = preparer(client)
    r = client.post("/dispensations", headers=officine, data={"numeroSerie": serie})
    assert r.status_code == 201


def test_deuxieme_dispensation_refusee_avec_alerte_de_reutilisation(client):
    serie, _, officine = preparer(client)
    client.post("/dispensations", headers=officine, data={"numeroSerie": serie})
    r = client.post("/dispensations", headers=officine, data={"numeroSerie": serie})
    assert r.status_code == 409 and "Reutilisation possible" in r.json()["detail"]
    db = session(client)
    assert db.get(Unite, serie).statut == StatutUnite.desactivee
    assert db.query(Evenement).count() == 3  # reception, dispensation, tentative gardee
    anomalie = db.query(Anomalie).one()
    assert anomalie.typeAnomalie.value == "reutilisationIdentifiant" and anomalie.statut == "a_verifier"


def test_sans_reception_la_dispensation_continue_avec_alerte_de_rupture(client):
    images, _ = serialiser(client)
    serie = next(iter(images))
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    r = client.post("/dispensations", headers=officine, data={"numeroSerie": serie})
    assert r.status_code == 201 and r.json()["alerte"] is True
    db = session(client)
    assert db.get(Unite, serie).statut == StatutUnite.desactivee
    assert db.query(Anomalie).one().typeAnomalie.value == "ruptureSequence"


def test_reception_par_une_autre_officine_compte_comme_rupture(client):
    serie, _, _ = preparer(client)
    db = session(client)
    db.add(ReferenceAutorisation(reference="TEST-OFF-002", nom="Autre officine", type=TypeStructure.officine))
    db.commit()
    autre = inscrire_structure(client, "officine", "TEST-OFF-002", "pharma2")
    r = client.post("/dispensations", headers=autre, data={"numeroSerie": serie})
    assert r.status_code == 201 and r.json()["alerte"] is True


def test_un_employe_de_lofficine_peut_dispenser(client):
    serie, _, officine = preparer(client)
    client.post("/employes", headers=officine, json={
        "nom": "Moussa Fall", "fonction": "Preparateur", "identifiantConnexion": "moussa.fall", "email": "moussa.fall" + "@essai.sn",
        "motDePasse": "MotDePasseEmploye1"})
    employe = connecte(client, "moussa.fall", "MotDePasseEmploye1")
    r = client.post("/dispensations", headers=employe, data={"numeroSerie": serie})
    assert r.status_code == 201 and r.json()["alerte"] is False  # la reception de l'officine compte


def test_seules_les_officines_dispensent(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    assert client.post("/dispensations", headers=fabricant, data={"numeroSerie": serie}).status_code == 403
    grossiste = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    assert client.post("/dispensations", headers=grossiste, data={"numeroSerie": serie}).status_code == 403


def test_identifiant_inconnu_et_code_illisible_refuses(client):
    _, _, officine = preparer(client)
    r = client.post("/dispensations", headers=officine, data={"numeroSerie": "INCONNU12345"})
    assert r.status_code == 404
    r = client.post("/dispensations", headers=officine,
                    files={"image": ("flou.png", b"image floue", "image/png")})
    assert r.status_code == 422 and "Code illisible" in r.json()["detail"]


def test_un_echec_ne_desactive_rien(client):
    serie, _, officine = preparer(client)
    client.post("/dispensations", headers=officine, data={"numeroSerie": "INCONNU12345"})
    assert session(client).get(Unite, serie).statut == StatutUnite.active


def test_sans_connexion_refuse(client):
    assert client.post("/dispensations", data={"numeroSerie": "X"}).status_code == 401
