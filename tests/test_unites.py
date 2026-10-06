"""Tests du cas Consulter le statut d'une unite (fiche 9)."""
from app.models import Evenement, ReferenceAutorisation, TypeStructure
from tests.test_evenements import inscrire_structure, serialiser, session


def test_unite_neuve_active_sans_evenement_ni_anomalie(client):
    images, fabricant = serialiser(client)
    serie, png = next(iter(images.items()))
    r = client.post("/unites/statut", headers=fabricant, files={"image": ("code.png", png, "image/png")})
    assert r.status_code == 200
    assert r.json() == {"numeroSerie": serie, "statut": "active",
                        "dernierEvenement": None, "anomalie": None}


def test_le_dernier_evenement_est_le_plus_recent(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    client.post("/evenements", headers=fabricant,
                data={"typeOperation": "expedition", "numeroSerie": serie,
                      "latitude": "14.69", "longitude": "-17.44"})
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    client.post("/evenements", headers=officine, data={"typeOperation": "reception", "numeroSerie": serie})
    r = client.post("/unites/statut", headers=officine, data={"numeroSerie": serie})
    assert r.json()["dernierEvenement"]["typeOperation"] == "reception"
    assert r.json()["dernierEvenement"]["latitude"] is None


def test_unite_dispensee_est_desactivee_avec_son_anomalie(client):
    images, _ = serialiser(client)
    serie = next(iter(images))
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    client.post("/dispensations", headers=officine, data={"numeroSerie": serie})  # sans reception: rupture
    r = client.post("/unites/statut", headers=officine, data={"numeroSerie": serie})
    corps = r.json()
    assert corps["statut"] == "desactivee"
    assert corps["dernierEvenement"]["typeOperation"] == "dispensation"
    assert corps["anomalie"]["typeAnomalie"] == "ruptureSequence"
    assert corps["anomalie"]["statut"] == "a_verifier"


def test_la_consultation_ne_modifie_rien(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    avant = session(client).query(Evenement).count()
    client.post("/unites/statut", headers=fabricant, data={"numeroSerie": serie})
    assert session(client).query(Evenement).count() == avant


def test_unite_inconnue_non_referencee(client):
    _, fabricant = serialiser(client)
    r = client.post("/unites/statut", headers=fabricant, data={"numeroSerie": "INCONNU12345"})
    assert r.status_code == 404 and "n'est pas referencee" in r.json()["detail"]


def test_code_illisible_demande_la_saisie(client):
    _, fabricant = serialiser(client)
    r = client.post("/unites/statut", headers=fabricant,
                    files={"image": ("flou.png", b"image floue", "image/png")})
    assert r.status_code == 422 and "Code illisible" in r.json()["detail"]


def test_un_fabricant_ne_consulte_que_ses_unites(client):
    images, _ = serialiser(client)
    serie = next(iter(images))
    db = session(client)
    db.add(ReferenceAutorisation(reference="TEST-FAB-002", nom="Autre labo", type=TypeStructure.fabricant))
    db.commit()
    autre = inscrire_structure(client, "fabricant", "TEST-FAB-002", "labo2")
    r = client.post("/unites/statut", headers=autre, data={"numeroSerie": serie})
    assert r.status_code == 403


def test_les_autres_acteurs_consultent_nimporte_quelle_unite(client):
    images, _ = serialiser(client)
    serie = next(iter(images))
    grossiste = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    for entete in (grossiste, officine):
        assert client.post("/unites/statut", headers=entete, data={"numeroSerie": serie}).status_code == 200


def test_la_pna_ne_consulte_pas(client):
    images, _ = serialiser(client)
    pna = inscrire_structure(client, "PNA", "TEST-PNA-001", "pna1")
    r = client.post("/unites/statut", headers=pna, data={"numeroSerie": next(iter(images))})
    assert r.status_code == 403


def test_sans_connexion_refuse(client):
    assert client.post("/unites/statut", data={"numeroSerie": "X"}).status_code == 401