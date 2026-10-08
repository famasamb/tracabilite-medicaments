"""Tests du cas Creer compte pharmacien chef de SR (fiche 4) et de la creation des SR."""
from app.models import Structure, TypeStructure
from tests.test_evenements import connecte, inscrire_structure, serialiser, session

CHEF = {"nom": "Awa Ndiaye", "fonction": "Pharmacien chef", "identifiantConnexion": "chef.dakar", "email": "chef.dakar" + "@essai.sn",
        "motDePasse": "MotDePasseChef1"}


def pna_connectee(client):
    return inscrire_structure(client, "PNA", "TEST-PNA-001", "pna1")


def test_linscription_dune_pna_cree_ses_14_sr_rattaches_a_elle(client):
    pna = pna_connectee(client)
    db = session(client)
    mere = db.query(Structure).filter_by(type=TypeStructure.PNA).one()
    sr = db.query(Structure).filter_by(type=TypeStructure.SR).all()
    assert len(sr) == 14 and all(s.mere_id == mere.id for s in sr)
    assert all(s.referenceAutorisation is None for s in sr)


def test_les_autres_structures_nont_pas_de_sr(client):
    inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    assert session(client).query(Structure).filter_by(type=TypeStructure.SR).count() == 0


def test_la_pna_liste_ses_sr(client):
    pna = pna_connectee(client)
    r = client.get("/sr", headers=pna)
    assert r.status_code == 200 and len(r.json()) == 14
    assert all(s["aUnResponsable"] is False for s in r.json())


def test_la_pna_cree_le_responsable_dun_sr(client):
    pna = pna_connectee(client)
    sr_id = client.get("/sr", headers=pna).json()[0]["id"]
    r = client.post(f"/sr/{sr_id}/responsable", headers=pna, json=CHEF)
    assert r.status_code == 201 and r.json()["structure_id"] == sr_id
    assert "motDePasse" not in r.text
    assert next(s for s in client.get("/sr", headers=pna).json() if s["id"] == sr_id)["aUnResponsable"]


def test_le_chef_de_sr_se_connecte_avec_les_droits_de_responsable(client):
    pna = pna_connectee(client)
    sr_id = client.get("/sr", headers=pna).json()[0]["id"]
    client.post(f"/sr/{sr_id}/responsable", headers=pna, json=CHEF)
    chef = connecte(client, "chef.dakar", "MotDePasseChef1")
    profil = client.get("/auth/moi", headers=chef).json()
    assert profil["role"] == "responsable" and profil["structure_type"] == "SR"
    # il peut creer des comptes pour son personnel (fiche 3)
    r = client.post("/employes", headers=chef, json={"nom": "Moussa Fall", "fonction": "Preparateur",
                    "identifiantConnexion": "moussa.sr", "email": "moussa.sr" + "@essai.sn", "motDePasse": "MotDePasseEmploye1"})
    assert r.status_code == 201


def test_le_chef_de_sr_peut_enregistrer_une_reception(client):
    images, _ = serialiser(client)
    pna = pna_connectee(client)
    sr_id = client.get("/sr", headers=pna).json()[0]["id"]
    client.post(f"/sr/{sr_id}/responsable", headers=pna, json=CHEF)
    chef = connecte(client, "chef.dakar", "MotDePasseChef1")
    r = client.post("/evenements", headers=chef,
                    data={"typeOperation": "reception", "numeroSerie": next(iter(images))})
    assert r.status_code == 201


def test_sr_deja_pourvu_refuse(client):                          # variante 4c
    pna = pna_connectee(client)
    sr_id = client.get("/sr", headers=pna).json()[0]["id"]
    client.post(f"/sr/{sr_id}/responsable", headers=pna, json=CHEF)
    r = client.post(f"/sr/{sr_id}/responsable", headers=pna,
                    json=dict(CHEF, identifiantConnexion="autre.chef"))
    assert r.status_code == 409 and "deja d" in r.json()["detail"]


def test_identifiant_deja_utilise_refuse(client):                # variante 4b
    pna = pna_connectee(client)
    ids = [s["id"] for s in client.get("/sr", headers=pna).json()]
    client.post(f"/sr/{ids[0]}/responsable", headers=pna, json=CHEF)
    r = client.post(f"/sr/{ids[1]}/responsable", headers=pna, json=CHEF)
    assert r.status_code == 409 and "identifiant" in r.json()["detail"]


def test_sr_inconnu_ou_dune_autre_structure_refuse(client):
    pna = pna_connectee(client)
    assert client.post("/sr/inexistant/responsable", headers=pna, json=CHEF).status_code == 404
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    officine_id = client.get("/auth/moi", headers=officine).json()["structure_id"]
    assert client.post(f"/sr/{officine_id}/responsable", headers=pna, json=CHEF).status_code == 404


def test_seule_la_pna_gere_les_sr(client):
    pna = pna_connectee(client)
    sr_id = client.get("/sr", headers=pna).json()[0]["id"]
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    assert client.get("/sr", headers=officine).status_code == 403
    assert client.post(f"/sr/{sr_id}/responsable", headers=officine, json=CHEF).status_code == 403


def test_un_employe_de_la_pna_ne_gere_pas_les_sr(client):
    pna = pna_connectee(client)
    client.post("/employes", headers=pna, json={"nom": "Moussa Fall", "fonction": "Agent",
                "identifiantConnexion": "agent.pna", "email": "agent.pna" + "@essai.sn", "motDePasse": "MotDePasseEmploye1"})
    agent = connecte(client, "agent.pna", "MotDePasseEmploye1")
    assert client.get("/sr", headers=agent).status_code == 403


def test_sans_connexion_refuse(client):
    assert client.get("/sr").status_code == 401
