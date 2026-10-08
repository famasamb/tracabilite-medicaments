"""Rupture de sequence a la reception: une unite recue sans que personne d'autre ne l'ait expediee."""
from app.models import Anomalie, StatutUnite, TypeOperation, Unite
from app.moteur_anomalies import Operation, analyser_unite
from tests.test_evenements import inscrire_structure, serialiser, session
from tests.test_moteur_anomalies import RUPTURE, op, types


def expedier(client, fabricant, serie):
    assert client.post("/evenements", headers=fabricant,
                       data={"typeOperation": "expedition", "numeroSerie": serie}).status_code == 201


def test_une_reception_sans_expedition_est_gardee_avec_une_alerte_de_rupture(client):
    images, _ = serialiser(client)
    serie = next(iter(images))
    sr = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    r = client.post("/evenements", headers=sr, data={"typeOperation": "reception", "numeroSerie": serie})
    assert r.status_code == 201
    corps = r.json()
    assert corps["alerte"] is True and corps["typeAnomalie"] == "ruptureSequence"
    assert "aucune expedition" in corps["message"]
    anomalie = session(client).query(Anomalie).one()
    assert anomalie.typeAnomalie.value == "ruptureSequence" and anomalie.statut == "a_verifier"


def test_une_reception_apres_l_expedition_du_fabricant_est_normale(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    expedier(client, fabricant, serie)
    sr = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    r = client.post("/evenements", headers=sr, data={"typeOperation": "reception", "numeroSerie": serie})
    assert r.status_code == 201 and r.json()["alerte"] is False and r.json()["typeAnomalie"] is None
    assert session(client).query(Anomalie).count() == 0


def test_sa_propre_expedition_ne_justifie_pas_sa_reception(client):
    images, _ = serialiser(client)
    serie = next(iter(images))
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    assert client.post("/evenements", headers=gros, data={"typeOperation": "expedition", "numeroSerie": serie}).status_code == 201
    r = client.post("/evenements", headers=gros, data={"typeOperation": "reception", "numeroSerie": serie})
    assert r.json()["typeAnomalie"] == "ruptureSequence"


def test_une_expedition_n_est_pas_concernee_par_cette_regle(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    r = client.post("/evenements", headers=fabricant, data={"typeOperation": "expedition", "numeroSerie": serie})
    assert r.json()["alerte"] is False


def test_sur_une_unite_desactivee_la_reutilisation_passe_avant_la_rupture(client):
    images, _ = serialiser(client)
    serie = next(iter(images))
    db = session(client)
    db.get(Unite, serie).statut = StatutUnite.desactivee
    db.commit()
    sr = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    r = client.post("/evenements", headers=sr, data={"typeOperation": "reception", "numeroSerie": serie})
    assert r.json()["typeAnomalie"] == "reutilisationIdentifiant"
    assert session(client).query(Anomalie).count() == 1


def test_le_moteur_signale_aussi_une_reception_sans_expedition():
    sans = [op("S1", TypeOperation.reception, 0, "gros", "r")]
    detections = analyser_unite(sans)
    assert [(d.evenement_id, d.type) for d in detections] == [("r", RUPTURE)]
    assert "reception sans expedition" in detections[0].description
    meme_structure = [op("S1", TypeOperation.expedition, 0, "gros"), op("S1", TypeOperation.reception, 5, "gros")]
    assert types(analyser_unite(meme_structure)) == [RUPTURE]
    normale = [op("S1", TypeOperation.expedition, 0, "fab"), op("S1", TypeOperation.reception, 5, "gros")]
    assert analyser_unite(normale) == []
