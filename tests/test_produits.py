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


def test_recherche_par_nom_et_par_gtin(client):
    inscrire(client)
    entete = connecte(client)
    client.post("/produits", json=dict(PRODUIT, gtin=GTIN_VALIDE), headers=entete)
    client.post("/produits", json=dict(PRODUIT, nom="Amoxicilline 500 mg"), headers=entete)
    par_nom = client.get("/produits", params={"q": "parace"}, headers=entete).json()
    assert [p["nom"] for p in par_nom] == ["Paracetamol 500 mg"]
    par_gtin = client.get("/produits", params={"q": GTIN_VALIDE}, headers=entete).json()
    assert len(par_gtin) == 1 and par_gtin[0]["gtin"] == GTIN_VALIDE
    assert client.get("/produits", params={"q": "introuvable"}, headers=entete).json() == []


def test_la_recherche_ne_montre_que_les_produits_de_son_laboratoire(client):
    from app.db import get_db
    from app.main import app as application
    from app.models import ReferenceAutorisation, TypeStructure
    inscrire(client)
    client.post("/produits", json=PRODUIT, headers=connecte(client))
    db = next(application.dependency_overrides[get_db]())
    db.add(ReferenceAutorisation(reference="TEST-FAB-002", nom="Autre labo", type=TypeStructure.fabricant))
    db.commit()
    client.post("/structures/inscription", json={
        "structure": {"nom": "Autre Laboratoire", "type": "fabricant", "localisation": "Thies",
                      "referenceAutorisation": "TEST-FAB-002"},
        "responsable": {"nom": "Ibrahima Sow", "fonction": "Pharmacien", "identifiantConnexion": "labo2",
                        "motDePasse": "MotDePasse2026"}})
    r = client.get("/produits", params={"q": "parace"}, headers=connecte(client, "labo2"))
    assert r.json() == []


def test_recherche_reservee_aux_fabricants_et_connectes(client):
    assert client.get("/produits", params={"q": "parace"}).status_code == 401