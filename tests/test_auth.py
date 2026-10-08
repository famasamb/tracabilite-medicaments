"""Tests du cas S'authentifier (fiche 1)."""
from datetime import timedelta

from app.auth import creer_jeton
from app.models import Role, Utilisateur


def inscrire(client, identifiant="awa.diop", mdp="MotDePasse2026"):
    r = client.post("/structures/inscription", json={
        "structure": {"nom": "Laboratoire Test", "type": "fabricant",
                      "localisation": "Dakar", "referenceAutorisation": "TEST-FAB-001"},
        "responsable": {"nom": "Awa Diop", "fonction": "Pharmacien responsable",
                        "identifiantConnexion": identifiant, "email": identifiant + "@essai.sn", "motDePasse": mdp}})
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


def changer(client, jeton, actuel, nouveau):
    return client.post("/auth/mot-de-passe", headers={"Authorization": f"Bearer {jeton}"},
                       json={"motDePasseActuel": actuel, "nouveauMotDePasse": nouveau})


def test_changement_de_mot_de_passe(client):
    inscrire(client)
    jeton = se_connecter(client).json()["access_token"]
    assert changer(client, jeton, "MotDePasse2026", "NouveauSecret77").status_code == 200
    assert se_connecter(client, mdp="MotDePasse2026").status_code == 401
    assert se_connecter(client, mdp="NouveauSecret77").status_code == 200


def test_changement_refuse_si_l_actuel_est_faux_trop_court_ou_identique(client):
    inscrire(client)
    jeton = se_connecter(client).json()["access_token"]
    assert changer(client, jeton, "Faux123456", "NouveauSecret77").status_code == 400
    assert changer(client, jeton, "MotDePasse2026", "court").status_code == 422
    assert changer(client, jeton, "MotDePasse2026", "MotDePasse2026").status_code == 422
    assert se_connecter(client).status_code == 200


def test_changement_reserve_aux_utilisateurs_connectes(client):
    r = client.post("/auth/mot-de-passe", json={"motDePasseActuel": "x", "nouveauMotDePasse": "NouveauSecret77"})
    assert r.status_code == 401


def test_un_employe_change_son_propre_mot_de_passe_sans_toucher_aux_autres(client):
    inscrire(client)
    jeton = se_connecter(client).json()["access_token"]
    entete = {"Authorization": f"Bearer {jeton}"}
    r = client.post("/employes", headers=entete, json={"nom": "Moussa Fall", "fonction": "Preparateur",
                    "identifiantConnexion": "moussa.fall", "email": "moussa.fall" + "@essai.sn", "motDePasse": "MotDePasse2026"})
    assert r.status_code == 201
    jeton_employe = se_connecter(client, "moussa.fall").json()["access_token"]
    assert changer(client, jeton_employe, "MotDePasse2026", "SecretEmploye88").status_code == 200
    assert se_connecter(client, "moussa.fall", "SecretEmploye88").status_code == 200
    assert se_connecter(client, "awa.diop", "MotDePasse2026").status_code == 200
