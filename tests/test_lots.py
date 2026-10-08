"""Tests du cas Serialiser un lot."""
import io
import zipfile
from datetime import date, timedelta

from app.codes import lire_code
from tests.test_auth import inscrire, se_connecter

PRODUIT = {"nom": "Paracetamol 500 mg", "composition": "Paracetamol 500 mg",
           "formePharmaceutique": "Comprime", "conditionnement": "Boite de 16",
           "gtin": "03760000000123"}
DEMAIN = (date.today() + timedelta(days=400)).isoformat()


def connecte(client, identifiant="awa.diop", mdp="MotDePasse2026"):
    jeton = se_connecter(client, identifiant, mdp).json()["access_token"]
    return {"Authorization": f"Bearer {jeton}"}


def preparer(client, produit=PRODUIT):
    inscrire(client)
    entete = connecte(client)
    pid = client.post("/produits", json=produit, headers=entete).json()["id"]
    return entete, pid


def lot(pid, numero="LOT2026A", quantite=5, peremption=DEMAIN):
    return {"produit_id": pid, "numeroLot": numero, "datePeremption": peremption, "quantite": quantite}


def test_serialisation_renvoie_un_zip_avec_une_image_par_unite(client):
    entete, pid = preparer(client)
    r = client.post("/lots/serialisation", json=lot(pid, quantite=5), headers=entete)
    assert r.status_code == 201 and r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert len(zf.namelist()) == 5 and all(n.endswith(".png") for n in zf.namelist())
    assert r.headers["x-message"] == "Lot LOT2026A serialise: 5 codes generes."


def test_les_codes_sont_relisibles_et_corrects(client):
    entete, pid = preparer(client)
    r = client.post("/lots/serialisation", json=lot(pid, quantite=3), headers=entete)
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    for nom in zf.namelist():
        serie = nom[:-4]
        texte = lire_code(zf.read(nom))
        assert texte is not None
        assert texte.startswith("(01)03760000000123(17)")
        assert "(10)LOT2026A" in texte and texte.endswith(f"(21){serie}")


def test_produit_sans_gtin_utilise_lidentifiant_interne(client):
    entete, pid = preparer(client, produit={k: v for k, v in PRODUIT.items() if k != "gtin"})
    r = client.post("/lots/serialisation", json=lot(pid, quantite=1), headers=entete)
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    texte = lire_code(zf.read(zf.namelist()[0]))
    assert "(01)" not in texte and texte.endswith(f"(91){pid}")


def test_les_unites_sont_enregistrees_actives_et_uniques(client):
    from app.db import get_db
    from app.main import app as application
    from app.models import Lot, StatutUnite
    entete, pid = preparer(client)
    client.post("/lots/serialisation", json=lot(pid, quantite=20), headers=entete)
    db = next(application.dependency_overrides[get_db]())
    enregistre = db.query(Lot).one()
    assert enregistre.quantite == 20 and len(enregistre.unites) == 20
    assert len({u.numeroSerie for u in enregistre.unites}) == 20
    assert all(u.statut == StatutUnite.active for u in enregistre.unites)


def test_lot_deja_serialise_refuse(client):
    entete, pid = preparer(client)
    client.post("/lots/serialisation", json=lot(pid), headers=entete)
    r = client.post("/lots/serialisation", json=lot(pid), headers=entete)
    assert r.status_code == 409 and "deja serialise" in r.json()["detail"]


def test_meme_numero_de_lot_pour_un_autre_produit_est_possible(client):
    entete, pid = preparer(client)
    pid2 = client.post("/produits", json=dict(PRODUIT, gtin=None, nom="Autre produit"), headers=entete).json()["id"]
    assert client.post("/lots/serialisation", json=lot(pid), headers=entete).status_code == 201
    assert client.post("/lots/serialisation", json=lot(pid2), headers=entete).status_code == 201


def test_produit_inconnu_refuse(client):
    entete, _ = preparer(client)
    r = client.post("/lots/serialisation", json=lot("inexistant"), headers=entete)
    assert r.status_code == 404


def test_date_de_peremption_passee_refusee(client):
    entete, pid = preparer(client)
    hier = (date.today() - timedelta(days=1)).isoformat()
    r = client.post("/lots/serialisation", json=lot(pid, peremption=hier), headers=entete)
    assert r.status_code == 422


def test_quantite_invalide_refusee(client):
    entete, pid = preparer(client)
    assert client.post("/lots/serialisation", json=lot(pid, quantite=0), headers=entete).status_code == 422
    assert client.post("/lots/serialisation", json=lot(pid, quantite=10001), headers=entete).status_code == 422


def test_un_fabricant_ne_peut_pas_serialiser_le_produit_dun_autre(client):
    entete, pid = preparer(client)
    # un second fabricant est inscrit avec une autre reference de la base de test
    from app.db import get_db
    from app.main import app as application
    from app.models import ReferenceAutorisation, TypeStructure
    db = next(application.dependency_overrides[get_db]())
    db.add(ReferenceAutorisation(reference="TEST-FAB-002", nom="Autre labo", type=TypeStructure.fabricant))
    db.commit()
    client.post("/structures/inscription", json={
        "structure": {"nom": "Autre Laboratoire", "type": "fabricant", "localisation": "Thies",
                      "referenceAutorisation": "TEST-FAB-002"},
        "responsable": {"nom": "Ibrahima Sow", "fonction": "Pharmacien", "identifiantConnexion": "labo2", "email": "labo2" + "@essai.sn",
                        "motDePasse": "MotDePasse2026"}})
    r = client.post("/lots/serialisation", json=lot(pid), headers=connecte(client, "labo2"))
    assert r.status_code == 403


def test_une_officine_ne_peut_pas_serialiser(client):
    client.post("/structures/inscription", json={
        "structure": {"nom": "Pharmacie Test", "type": "officine", "localisation": "Dakar",
                      "referenceAutorisation": "TEST-OFF-001"},
        "responsable": {"nom": "Awa Diop", "fonction": "Pharmacien", "identifiantConnexion": "pharma1", "email": "pharma1" + "@essai.sn",
                        "motDePasse": "MotDePasse2026"}})
    r = client.post("/lots/serialisation", json=lot("x"), headers=connecte(client, "pharma1"))
    assert r.status_code == 403


def test_sans_connexion_refuse(client):
    assert client.post("/lots/serialisation", json=lot("x")).status_code == 401
