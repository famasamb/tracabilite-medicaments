"""Tests du cas S'inscrire (fiche 2)."""


def demande(reference="TEST-FAB-001", type_="fabricant", identifiant="resp.fab", mdp="MotDePasse2026"):
    return {
        "structure": {"nom": "Laboratoire Test", "type": type_,
                      "localisation": "Dakar", "referenceAutorisation": reference},
        "responsable": {"nom": "Awa Diop", "fonction": "Pharmacien responsable",
                        "identifiantConnexion": identifiant, "email": identifiant + "@essai.sn", "motDePasse": mdp},
    }


def test_inscription_reussie(client):
    r = client.post("/structures/inscription", json=demande())
    assert r.status_code == 201
    assert r.json()["structure_id"] and r.json()["utilisateur_id"]


def test_la_reponse_ne_contient_jamais_le_mot_de_passe(client):
    r = client.post("/structures/inscription", json=demande())
    assert "MotDePasse2026" not in r.text and "scrypt" not in r.text


def test_reference_inconnue_refusee(client):                          # variante 3c
    r = client.post("/structures/inscription", json=demande(reference="INCONNUE-9"))
    assert r.status_code == 422 and "ARP" in r.json()["detail"]


def test_reference_d_un_autre_type_refusee(client):
    r = client.post("/structures/inscription", json=demande(reference="TEST-OFF-001", type_="fabricant"))
    assert r.status_code == 422


def test_structure_deja_inscrite_refusee(client):                     # variante 3b
    assert client.post("/structures/inscription", json=demande()).status_code == 201
    r = client.post("/structures/inscription", json=demande(identifiant="autre.compte"))
    assert r.status_code == 409


def test_identifiant_deja_utilise_refuse(client):
    assert client.post("/structures/inscription", json=demande()).status_code == 201
    r = client.post("/structures/inscription",
                    json=demande(reference="TEST-GRO-001", type_="grossisteRepartiteur"))
    assert r.status_code == 409


def test_un_sr_ne_peut_pas_s_inscrire(client):
    r = client.post("/structures/inscription", json=demande(type_="SR"))
    assert r.status_code == 403


def test_mot_de_passe_trop_court_refuse(client):
    assert client.post("/structures/inscription", json=demande(mdp="court")).status_code == 422


def test_les_quatre_types_autorises_peuvent_s_inscrire(client):
    cas = [("TEST-FAB-001", "fabricant"), ("TEST-GRO-001", "grossisteRepartiteur"),
           ("TEST-OFF-001", "officine"), ("TEST-PNA-001", "PNA")]
    for i, (ref, type_) in enumerate(cas):
        r = client.post("/structures/inscription", json=demande(ref, type_, identifiant=f"resp{i}"))
        assert r.status_code == 201, (type_, r.text)
