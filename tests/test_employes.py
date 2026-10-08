"""Tests du cas Creer un compte employe (fiche 3)."""
from tests.test_auth import inscrire, se_connecter

EMPLOYE = {"nom": "Moussa Fall", "fonction": "Preparateur", "identifiantConnexion": "moussa.fall", "email": "moussa.fall" + "@essai.sn",
           "motDePasse": "MotDePasseEmploye1"}


def en_tete(client, identifiant="awa.diop", mdp="MotDePasse2026"):
    jeton = se_connecter(client, identifiant, mdp).json()["access_token"]
    return {"Authorization": f"Bearer {jeton}"}


def test_le_responsable_cree_un_employe_de_sa_structure(client):
    inscription = inscrire(client)
    r = client.post("/employes", json=EMPLOYE, headers=en_tete(client))
    assert r.status_code == 201
    assert r.json()["structure_id"] == inscription["structure_id"]
    assert "motDePasse" not in r.text


def test_lemploye_peut_se_connecter_avec_role_employe(client):
    inscrire(client)
    client.post("/employes", json=EMPLOYE, headers=en_tete(client))
    entete = en_tete(client, "moussa.fall", "MotDePasseEmploye1")
    profil = client.get("/auth/moi", headers=entete).json()
    assert profil["role"] == "employe" and profil["structure_type"] == "fabricant"


def test_identifiant_deja_utilise_refuse(client):
    inscrire(client)
    client.post("/employes", json=EMPLOYE, headers=en_tete(client))
    r = client.post("/employes", json=EMPLOYE, headers=en_tete(client))
    assert r.status_code == 409


def test_un_employe_ne_peut_pas_creer_de_compte(client):
    inscrire(client)
    client.post("/employes", json=EMPLOYE, headers=en_tete(client))
    autre = dict(EMPLOYE, identifiantConnexion="autre.employe")
    r = client.post("/employes", json=autre, headers=en_tete(client, "moussa.fall", "MotDePasseEmploye1"))
    assert r.status_code == 403


def test_sans_connexion_refuse(client):
    assert client.post("/employes", json=EMPLOYE).status_code == 401


def test_mot_de_passe_trop_court_refuse(client):
    inscrire(client)
    r = client.post("/employes", json=dict(EMPLOYE, motDePasse="court"), headers=en_tete(client))
    assert r.status_code == 422
