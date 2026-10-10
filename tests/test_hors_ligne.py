"""Operations faites sans reseau: date reelle, identifiant du telephone, envoi repete sans doublon."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, inspect, text

from app.migration import mettre_a_niveau
from app.models import Anomalie, Evenement, maintenant
from tests.test_dispensations import preparer
from tests.test_evenements import inscrire_structure, serialiser, session

ID = "tel-0001-abcdef"


def iso(date):
    return date.replace(tzinfo=timezone.utc).isoformat()


def test_la_date_du_telephone_est_conservee(client):
    serie, _, officine = preparer(client)
    avant = maintenant() - timedelta(hours=3)
    r = client.post("/dispensations", headers=officine,
                    data={"numeroSerie": serie, "dateHeure": iso(avant), "identifiantClient": ID})
    assert r.status_code == 201
    enregistre = session(client).query(Evenement).filter_by(identifiantClient=ID).one()
    assert abs(enregistre.dateHeure - avant) < timedelta(seconds=1)


def test_la_date_sans_fuseau_est_lue_comme_utc(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    avant = (maintenant() - timedelta(hours=2)).replace(microsecond=0)
    r = client.post("/evenements", headers=fabricant, data={
        "typeOperation": "expedition", "numeroSerie": serie, "dateHeure": avant.isoformat(), "identifiantClient": ID})
    assert r.status_code == 201
    assert session(client).query(Evenement).one().dateHeure == avant


def test_une_date_dans_le_futur_ou_trop_ancienne_est_remplacee_par_celle_du_serveur(client):
    images, fabricant = serialiser(client, quantite=2)
    s1, s2 = list(images)
    for serie, date in ((s1, maintenant() + timedelta(days=2)), (s2, maintenant() - timedelta(days=90))):
        r = client.post("/evenements", headers=fabricant,
                        data={"typeOperation": "expedition", "numeroSerie": serie, "dateHeure": iso(date)})
        assert r.status_code == 201
    for e in session(client).query(Evenement).all():
        assert abs(e.dateHeure - maintenant()) < timedelta(minutes=1)


def test_un_envoi_repete_ne_cree_pas_de_doublon(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    donnees = {"typeOperation": "expedition", "numeroSerie": serie, "identifiantClient": ID}
    premier = client.post("/evenements", headers=fabricant, data=donnees)
    second = client.post("/evenements", headers=fabricant, data=donnees)
    assert premier.status_code == 201 and second.status_code == 200
    assert premier.json()["id"] == second.json()["id"] and premier.json()["dateHeure"] == second.json()["dateHeure"]
    assert session(client).query(Evenement).count() == 1


def test_un_envoi_repete_renvoie_la_meme_alerte(client):
    images, _ = serialiser(client)
    serie = next(iter(images))
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    donnees = {"typeOperation": "reception", "numeroSerie": serie, "identifiantClient": ID}
    premier = client.post("/evenements", headers=officine, data=donnees).json()
    second = client.post("/evenements", headers=officine, data=donnees).json()
    assert premier["alerte"] is True and second["alerte"] is True
    assert second["typeAnomalie"] == "ruptureSequence"
    db = session(client)
    assert db.query(Evenement).count() == 1 and db.query(Anomalie).count() == 1


def test_une_dispensation_refusee_reste_refusee_si_l_envoi_est_repete(client):
    serie, _, officine = preparer(client)
    client.post("/dispensations", headers=officine, data={"numeroSerie": serie, "identifiantClient": "premier-envoi-1"})
    donnees = {"numeroSerie": serie, "identifiantClient": ID}
    refus = client.post("/dispensations", headers=officine, data=donnees)
    encore = client.post("/dispensations", headers=officine, data=donnees)
    assert refus.status_code == 409 and encore.status_code == 409
    assert session(client).query(Evenement).filter_by(identifiantClient=ID).count() == 1
    assert session(client).query(Anomalie).count() == 1


def test_la_dispensation_envoyee_deux_fois_ne_desactive_et_ne_compte_qu_une_fois(client):
    serie, _, officine = preparer(client)
    donnees = {"numeroSerie": serie, "identifiantClient": ID}
    assert client.post("/dispensations", headers=officine, data=donnees).status_code == 201
    assert client.post("/dispensations", headers=officine, data=donnees).status_code == 200
    assert session(client).query(Evenement).count() == 3     # expedition, reception, dispensation
    assert session(client).query(Anomalie).count() == 0


def test_l_identifiant_du_telephone_est_propre_a_chaque_utilisateur(client):
    images, fabricant = serialiser(client, quantite=1)
    serie = next(iter(images))
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    r1 = client.post("/evenements", headers=fabricant,
                     data={"typeOperation": "expedition", "numeroSerie": serie, "identifiantClient": ID})
    r2 = client.post("/evenements", headers=officine,
                     data={"typeOperation": "reception", "numeroSerie": serie, "identifiantClient": ID})
    assert r1.status_code == 201 and r2.status_code == 201
    assert session(client).query(Evenement).count() == 2


def test_identifiant_invalide_refuse(client):
    images, fabricant = serialiser(client)
    serie = next(iter(images))
    for mauvais in ("court", "avec espace dedans", "x" * 65, "accentué-123456"):
        r = client.post("/evenements", headers=fabricant,
                        data={"typeOperation": "expedition", "numeroSerie": serie, "identifiantClient": mauvais})
        assert r.status_code == 422, mauvais


def test_sans_identifiant_le_comportement_reste_inchange(client):
    images, fabricant = serialiser(client, quantite=1)
    serie = next(iter(images))
    r = client.post("/evenements", headers=fabricant, data={"typeOperation": "expedition", "numeroSerie": serie})
    assert r.status_code == 201
    assert session(client).query(Evenement).one().identifiantClient is None


def test_la_mise_a_niveau_ajoute_la_colonne_a_une_ancienne_base(tmp_path):
    chemin = tmp_path / "ancienne.db"
    moteur = create_engine(f"sqlite:///{chemin.as_posix()}")
    mettre_a_niveau(moteur)
    with moteur.begin() as c:   # on remet la table dans l'etat d'avant la fonctionnalite
        c.execute(text("DROP INDEX IF EXISTS uq_evenement_client"))
        c.execute(text('ALTER TABLE evenements DROP COLUMN "identifiantClient"'))
    assert "identifiantClient" not in {c["name"] for c in inspect(moteur).get_columns("evenements")}
    mettre_a_niveau(moteur)
    mettre_a_niveau(moteur)     # sans effet la deuxieme fois
    assert "identifiantClient" in {c["name"] for c in inspect(moteur).get_columns("evenements")}
