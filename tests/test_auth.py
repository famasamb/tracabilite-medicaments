"""Tests du cas S'authentifier (fiche 1)."""
from datetime import timedelta

from app.auth import creer_jeton
from app.models import Role, Utilisateur


def inscrire(client, identifiant="awa.diop", mdp="MotDePasse2026"):
    r = client.post("/structures/inscription", json={
        "structure": {"nom": "Laboratoire Test", "type": "fabricant",
                      "localisation": "Dakar", "referenceAutorisation": "TEST-FAB-001"},
        "responsable": {"nom": "Awa Diop", "fonction": "Pharmacien responsable",
                        "identifiantConnexion": identifiant, "motDePasse": mdp}})
    assert r.status_code == 201
    return r.json()


def se_connecter(client, identifiant="awa.diop", mdp="MotDePasse2026"):
    return client.post("/auth/connexion", data={"username": identifiant, "password": mdp})


def test_connexion_reussie_donne_un_jeton(client):
    inscrire(client)
    r = se_connecter(client)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer" and r.json()["access_token"]


def test_le_jeton_donne_acces_au_profil(client):
    inscrire(client)
    jeton = se_connecter(client).json()["access_token"]
    r = client.get("/auth/moi", headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code == 200
    profil = r.json()
    assert profil["role"] == "responsable" and profil["structure_type"] == "fabricant"
    assert "motDePasse" not in r.text


def test_mauvais_mot_de_passe_refuse(client):                          # variante 3b
    inscrire(client)
    r = se_connecter(client, mdp="MauvaisMotDePasse")
    assert r.status_code == 401 and "incorrect" in r.json()["detail"]


def test_compte_inconnu_refuse(client):                                # variante 3c
    r = se_connecter(client, identifiant="personne")
    assert r.status_code == 401 and "responsable" in r.json()["detail"]


def test_sans_jeton_acces_refuse(client):
    assert client.get("/auth/moi").status_code == 401


def test_jeton_falsifie_refuse(client):
    inscrire(client)
    jeton = se_connecter(client).json()["access_token"]
    r = client.get("/auth/moi", headers={"Authorization": f"Bearer {jeton}x"})
    assert r.status_code == 401


def test_jeton_expire_refuse(client):
    ids = inscrire(client)
    utilisateur = Utilisateur(id=ids["utilisateur_id"], role=Role.responsable)
    jeton_expire = creer_jeton(utilisateur, duree=timedelta(seconds=-10))
    r = client.get("/auth/moi", headers={"Authorization": f"Bearer {jeton_expire}"})
    assert r.status_code == 401