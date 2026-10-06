"""Tests du cas Consulter le tableau de bord du circuit public (fiche 10)."""
from datetime import datetime, timedelta, timezone

from app.models import StatutUnite, Unite
from tests.test_evenements import connecte, inscrire_structure, serialiser, session

AUJOURDHUI = datetime.now(timezone.utc).date()


def creer_chef(client, pna, indice, identifiant):
    sr = client.get("/sr", headers=pna).json()[indice]
    r = client.post(f"/sr/{sr['id']}/responsable", headers=pna, json={
        "nom": "Chef Test", "fonction": "Pharmacien chef", "identifiantConnexion": identifiant,
        "motDePasse": "MotDePasseChef1"})
    assert r.status_code == 201
    return sr["id"], connecte(client, identifiant, "MotDePasseChef1")


def reception(client, entete, serie, gps=True):
    data = {"typeOperation": "reception", "numeroSerie": serie}
    if gps:
        data.update(latitude="14.69", longitude="-17.44")
    assert client.post("/evenements", headers=entete, data=data).status_code == 201


def scenario(client):
    """PNA avec 2 SR actifs. Dakar: 2 receptions (1 avec GPS). Diourbel: 2 receptions avec GPS,
    dont une unite deja desactivee (alerte). Une officine recoit aussi une unite (hors circuit public)."""
    images, _ = serialiser(client, quantite=5)
    series = list(images)
    db = session(client)
    db.get(Unite, series[3]).statut = StatutUnite.desactivee
    db.commit()
    pna = inscrire_structure(client, "PNA", "TEST-PNA-001", "pna1")
    dakar_id, dakar = creer_chef(client, pna, 0, "chef.dakar")
    diourbel_id, diourbel = creer_chef(client, pna, 1, "chef.diourbel")
    reception(client, dakar, series[0], gps=True)
    reception(client, dakar, series[1], gps=False)
    reception(client, diourbel, series[2], gps=True)
    reception(client, diourbel, series[3], gps=True)  # unite desactivee: anomalie
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    reception(client, officine, series[4], gps=True)
    return pna, dakar_id, diourbel_id, series


def test_vue_densemble_des_sr_seulement(client):
    pna, _, _, _ = scenario(client)
    r = client.get("/tableau-de-bord", headers=pna)
    assert r.status_code == 200
    t = r.json()
    assert t["nombreEvenements"] == 4          # l'officine n'est pas comptee
    assert t["unitesSuivies"] == 4
    assert t["anomaliesSignalees"] == 1
    assert t["anomaliesParType"] == {"reutilisationIdentifiant": 1}
    assert len(t["pointsCarte"]) == 3          # l'evenement sans position n'est pas sur la carte
    assert t["message"] is None
    assert "signaux a verifier" in t["avertissement"]


def test_alertes_recentes(client):
    pna, _, diourbel_id, series = scenario(client)
    alertes = client.get("/tableau-de-bord", headers=pna).json()["alertesRecentes"]
    assert len(alertes) == 1
    assert alertes[0]["numeroSerie"] == series[3] and alertes[0]["sr"] == "SR Diourbel"
    assert alertes[0]["statut"] == "a_verifier"


def test_filtre_par_sr(client):
    pna, dakar_id, diourbel_id, _ = scenario(client)
    dakar = client.get("/tableau-de-bord", headers=pna, params={"sr_id": dakar_id}).json()
    assert dakar["nombreEvenements"] == 2 and dakar["anomaliesSignalees"] == 0
    assert len(dakar["pointsCarte"]) == 1 and {p["sr"] for p in dakar["pointsCarte"]} == {"SR Dakar"}
    diourbel = client.get("/tableau-de-bord", headers=pna, params={"sr_id": diourbel_id}).json()
    assert diourbel["nombreEvenements"] == 2 and diourbel["anomaliesSignalees"] == 1


def test_filtre_par_periode(client):
    pna, _, _, _ = scenario(client)
    jour = {"du": AUJOURDHUI.isoformat(), "au": AUJOURDHUI.isoformat()}
    assert client.get("/tableau-de-bord", headers=pna, params=jour).json()["nombreEvenements"] == 4


def test_aucun_evenement_pour_le_filtre(client):                 # variante 4b
    pna, _, _, _ = scenario(client)
    demain = (AUJOURDHUI + timedelta(days=1)).isoformat()
    r = client.get("/tableau-de-bord", headers=pna, params={"du": demain})
    assert r.status_code == 200
    t = r.json()
    assert t["nombreEvenements"] == 0 and t["pointsCarte"] == [] and t["alertesRecentes"] == []
    assert "Aucun evenement" in t["message"]


def test_dates_inversees_refusees(client):
    pna, _, _, _ = scenario(client)
    r = client.get("/tableau-de-bord", headers=pna, params={"du": "2026-12-31", "au": "2026-01-01"})
    assert r.status_code == 422


def test_sr_inconnu_ou_dune_autre_structure_refuse(client):
    pna, _, _, _ = scenario(client)
    assert client.get("/tableau-de-bord", headers=pna, params={"sr_id": "inexistant"}).status_code == 404
    officine = connecte(client, "pharma1")
    officine_id = client.get("/auth/moi", headers=officine).json()["structure_id"]
    assert client.get("/tableau-de-bord", headers=pna, params={"sr_id": officine_id}).status_code == 404


def test_pna_sans_activite(client):
    pna = inscrire_structure(client, "PNA", "TEST-PNA-001", "pna1")
    t = client.get("/tableau-de-bord", headers=pna).json()
    assert t["nombreEvenements"] == 0 and "Aucun evenement" in t["message"]


def test_la_consultation_ne_modifie_rien(client):
    from app.models import Anomalie, Evenement
    pna, _, _, _ = scenario(client)
    db = session(client)
    avant = (db.query(Evenement).count(), db.query(Anomalie).count())
    client.get("/tableau-de-bord", headers=pna)
    assert (db.query(Evenement).count(), db.query(Anomalie).count()) == avant


def test_reserve_a_la_pna(client):
    pna, _, _, _ = scenario(client)
    officine = connecte(client, "pharma1")
    assert client.get("/tableau-de-bord", headers=officine).status_code == 403
    chef_sr = connecte(client, "chef.dakar", "MotDePasseChef1")
    assert client.get("/tableau-de-bord", headers=chef_sr).status_code == 403
    assert client.get("/tableau-de-bord").status_code == 401