"""Tests du cas Enregistrer les informations d'un produit."""
from app.codes import cle_de_controle_gtin
from tests.test_auth import inscrire, se_connecter

PRODUIT = {"nom": "Paracetamol 500 mg", "composition": "Paracetamol 500 mg",
           "formePharmaceutique": "Comprime", "conditionnement": "Boite de 16"}
BASE_GTIN = "0376000000012"  # 13 premiers chiffres; on ajoute la cle de controle calculee
GTIN_VALIDE = BASE_GTIN + str(cle_de_controle_gtin(BASE_GTIN))


def connecte(client, identifiant="awa.diop", mdp="MotDePasse2026"):
    jeton = se_connecter(client, identifiant, mdp).json()["access_token"]
    return {"Authorization": f"Bearer {jeton}"}


def test_le_fabricant_enregistre_un_produit_avec_gtin(client):
    inscrire(client)
    r = client.post("/produits", json=dict(PRODUIT, gtin=GTIN_VALIDE), headers=connecte(client))
    assert r.status_code == 201
    assert r.json()["gtin"] == GTIN_VALIDE and r.json()["laboratoire"] == "Laboratoire Test"


def test_produit_sans_gtin_accepte(client):
    inscrire(client)
    r = client.post("/produits", json=PRODUIT, headers=connecte(client))
    assert r.status_code == 201 and r.json()["gtin"] is None


def test_deux_produits_sans_gtin_sont_possibles(client):
    inscrire(client)
    entete = connecte(client)
    assert client.post("/produits", json=PRODUIT, headers=entete).status_code == 201
    assert client.post("/produits", json=dict(PRODUIT, nom="Autre"), headers=entete).status_code == 201


def test_gtin_invalide_refuse(client):
    inscrire(client)
    mauvais = GTIN_VALIDE[:13] + str((int(GTIN_VALIDE[13]) + 1) % 10)
    r = client.post("/produits", json=dict(PRODUIT, gtin=mauvais), headers=connecte(client))
    assert r.status_code == 422


def test_gtin_deja_utilise_refuse(client):
    inscrire(client)
    entete = connecte(client)
    client.post("/produits", json=dict(PRODUIT, gtin=GTIN_VALIDE), headers=entete)
    r = client.post("/produits", json=dict(PRODUIT, gtin=GTIN_VALIDE), headers=entete)
    assert r.status_code == 409


def test_un_employe_du_fabricant_peut_enregistrer(client):
    inscrire(client)
    client.post("/employes", json={"nom": "Moussa Fall", "fonction": "Preparateur",
                "identifiantConnexion": "moussa.fall", "motDePasse": "MotDePasseEmploye1"},
                headers=connecte(client))
    r = client.post("/produits", json=PRODUIT, headers=connecte(client, "moussa.fall", "MotDePasseEmploye1"))
    assert r.status_code == 201


def test_une_officine_ne_peut_pas_enregistrer_de_produit(client):
    client.post("/structures/inscription", json={
        "structure": {"nom": "Pharmacie Test", "type": "officine", "localisation": "Dakar",
                      "referenceAutorisation": "TEST-OFF-001"},
        "responsable": {"nom": "Awa Diop", "fonction": "Pharmacien", "identifiantConnexion": "pharma1",
                        "motDePasse": "MotDePasse2026"}})
    r = client.post("/produits", json=PRODUIT, headers=connecte(client, "pharma1"))
    assert r.status_code == 403


def test_sans_connexion_refuse(client):
    assert client.post("/produits", json=PRODUIT).status_code == 401