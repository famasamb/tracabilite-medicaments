"""Expedition repetee: une unite ou un conteneur deja expedie (pas encore recu) ne peut pas l'etre de nouveau,
et seule la structure qui detient un conteneur peut l'expedier."""
from app.domaine.models import Evenement
from tests.test_conteneurs import circuit, composer, evenements, operer
from tests.test_evenements import inscrire_structure, serialiser


def test_un_carton_deja_expedie_ne_s_expedie_pas_deux_fois(client):
    images, fab, sscc = circuit(client, quantite=3)
    assert operer(client, fab, "expedition", sscc).status_code == 201
    r = operer(client, fab, "expedition", sscc)
    assert r.status_code == 409 and "deja ete expedie" in r.json()["detail"]
    assert len(evenements(client)) == 3          # rien n'a ete ajoute


def test_une_palette_deja_expediee_ne_s_expedie_pas_deux_fois(client):
    images, fab = serialiser(client, quantite=4)
    series = list(images)
    a = composer(client, fab, "carton", series[:2]).json()["sscc"]
    b = composer(client, fab, "carton", series[2:]).json()["sscc"]
    p = composer(client, fab, "palette", [a, b]).json()["sscc"]
    assert operer(client, fab, "expedition", p).status_code == 201
    assert operer(client, fab, "expedition", p).status_code == 409
    assert len(evenements(client)) == 4


def test_un_envoi_hors_ligne_repete_reste_accepte(client):
    """Le meme envoi (meme identifiantClient) renvoie le meme resultat: ce n'est pas une nouvelle expedition."""
    images, fab, sscc = circuit(client)
    r1 = operer(client, fab, "expedition", sscc, identifiantClient="envoi-0001")
    r2 = operer(client, fab, "expedition", sscc, identifiantClient="envoi-0001")
    assert r1.status_code == 201 and r2.status_code == 200
    assert len(evenements(client)) == 3


def test_un_autre_scan_du_meme_carton_apres_l_envoi_est_refuse(client):
    images, fab, sscc = circuit(client)
    assert operer(client, fab, "expedition", sscc, identifiantClient="envoi-0001").status_code == 201
    assert operer(client, fab, "expedition", sscc, identifiantClient="envoi-0002").status_code == 409


def test_une_boite_seule_deja_expediee_ne_s_expedie_pas_deux_fois(client):
    images, fab = serialiser(client, quantite=2)
    serie = next(iter(images))
    donnees = {"typeOperation": "expedition", "numeroSerie": serie}
    assert client.post("/evenements", headers=fab, data=donnees).status_code == 201
    r = client.post("/evenements", headers=fab, data=donnees)
    assert r.status_code == 409 and "deja ete expediee" in r.json()["detail"]
    assert session_evenements(client, serie) == 1


def session_evenements(client, serie):
    from tests.test_evenements import session
    return session(client).query(Evenement).filter_by(numeroSerie=serie).count()


def test_apres_la_reception_le_grossiste_peut_expedier(client):
    images, fab, sscc = circuit(client, quantite=2)
    operer(client, fab, "expedition", sscc)
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    assert operer(client, gros, "reception", sscc).status_code == 201
    r = operer(client, gros, "expedition", sscc)
    assert r.status_code == 201 and r.json()["nombreAlertes"] == 0
    # et il ne peut pas non plus l'expedier une seconde fois
    assert operer(client, gros, "expedition", sscc).status_code == 409


def test_seule_la_structure_qui_detient_le_conteneur_l_expedie(client):
    images, fab, sscc = circuit(client, quantite=2)
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    r = operer(client, gros, "expedition", sscc)       # le carton est encore chez le fabricant
    assert r.status_code == 403 and "pas chez vous" in r.json()["detail"]
    assert len(evenements(client)) == 0


def test_le_fabricant_ne_peut_plus_expedier_un_carton_qu_il_a_deja_envoye_au_grossiste(client):
    images, fab, sscc = circuit(client, quantite=2)
    operer(client, fab, "expedition", sscc)
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    operer(client, gros, "reception", sscc)           # le carton est maintenant chez le grossiste
    r = operer(client, fab, "expedition", sscc)
    assert r.status_code == 403


def palette_de_deux_cartons(client):
    images, fab = serialiser(client, quantite=4)
    series = list(images)
    a = composer(client, fab, "carton", series[:2]).json()["sscc"]
    b = composer(client, fab, "carton", series[2:]).json()["sscc"]
    p = composer(client, fab, "palette", [a, b]).json()["sscc"]
    return fab, a, b, p


def test_un_carton_sur_une_palette_ne_s_expedie_pas_seul(client):
    fab, a, b, p = palette_de_deux_cartons(client)
    r = operer(client, fab, "expedition", a)
    assert r.status_code == 409 and "sur une palette" in r.json()["detail"]
    assert len(evenements(client)) == 0


def test_la_palette_reste_expediable_apres_le_refus_d_un_carton(client):
    fab, a, b, p = palette_de_deux_cartons(client)
    operer(client, fab, "expedition", a)
    assert operer(client, fab, "expedition", p).status_code == 201
    assert len(evenements(client)) == 4


def test_un_carton_sur_une_palette_ne_se_recoit_pas_seul(client):
    fab, a, b, p = palette_de_deux_cartons(client)
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    operer(client, fab, "expedition", p)
    r = operer(client, gros, "reception", a)
    assert r.status_code == 409 and "sur une palette" in r.json()["detail"]
    assert operer(client, gros, "reception", p).status_code == 201


def test_apres_l_ouverture_de_la_palette_ses_cartons_s_expedient_seuls(client):
    fab, a, b, p = palette_de_deux_cartons(client)
    assert client.post(f"/conteneurs/{p}/ouvrir", headers=fab, json={}).status_code in (200, 201)
    assert operer(client, fab, "expedition", a).status_code == 201
    assert operer(client, fab, "expedition", b).status_code == 201
