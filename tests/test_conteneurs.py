"""Tests de l'agregation, etape 1: composer un carton ou une palette (fiche de conception de l'agregation)."""
from app.services.agregation import generer_sscc, sscc_valide
from app.services.codes import lire_code
from app.domaine.models import Contenu, Conteneur, EtatConteneur, ReferenceAutorisation, TypeStructure
from tests.test_evenements import connecte, inscrire_structure, serialiser, session


def composer(client, entete, niveau, elements):
    return client.post("/conteneurs", headers=entete, json={"niveau": niveau, "elements": elements})


def test_le_sscc_a_18_chiffres_et_une_cle_de_controle_valide():
    for _ in range(50):
        sscc = generer_sscc()
        assert len(sscc) == 18 and sscc.isdigit() and sscc_valide(sscc)
    faux = sscc[:17] + str((int(sscc[17]) + 1) % 10)
    assert not sscc_valide(faux)


def test_composer_un_carton(client):
    images, fab = serialiser(client, quantite=3)
    series = list(images)
    r = composer(client, fab, "carton", series[:2])
    assert r.status_code == 201
    c = r.json()
    assert sscc_valide(c["sscc"]) and c["niveau"] == "carton" and c["etat"] == "actif"
    assert sorted(c["elements"]) == sorted(series[:2]) and c["nombreBoites"] == 2
    assert session(client).query(Contenu).count() == 2


def test_une_boite_ne_peut_pas_etre_dans_deux_cartons(client):
    images, fab = serialiser(client, quantite=3)
    series = list(images)
    assert composer(client, fab, "carton", series[:2]).status_code == 201
    r = composer(client, fab, "carton", series[1:])
    assert r.status_code == 409 and "deja dans un carton" in r.json()["detail"]


def test_composer_une_palette_de_cartons(client):
    images, fab = serialiser(client, quantite=4)
    series = list(images)
    a = composer(client, fab, "carton", series[:2]).json()["sscc"]
    b = composer(client, fab, "carton", series[2:]).json()["sscc"]
    r = composer(client, fab, "palette", [a, b])
    assert r.status_code == 201
    p = r.json()
    assert p["niveau"] == "palette" and sorted(p["elements"]) == sorted([a, b]) and p["nombreBoites"] == 4
    # un carton ne peut pas etre sur deux palettes
    r2 = composer(client, fab, "palette", [a])
    assert r2.status_code == 409 and "deja sur une palette" in r2.json()["detail"]


def test_une_palette_n_accepte_que_des_cartons(client):
    images, fab = serialiser(client, quantite=2)
    serie = next(iter(images))
    r = composer(client, fab, "palette", [serie])
    assert r.status_code == 404


def test_elements_inconnus_refuses(client):
    images, fab = serialiser(client)
    assert composer(client, fab, "carton", ["ZZZZZZZZZZZZ"]).status_code == 404


def test_liste_vide_ou_doublons_refuses(client):
    images, fab = serialiser(client)
    serie = next(iter(images))
    assert composer(client, fab, "carton", []).status_code == 422
    assert composer(client, fab, "carton", [serie, serie]).status_code == 422


def test_seul_un_fabricant_compose(client):
    images, fab = serialiser(client)
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    assert composer(client, officine, "carton", [next(iter(images))]).status_code == 403


def test_un_fabricant_ne_compose_pas_avec_les_boites_d_un_autre(client):
    images, fab = serialiser(client)
    db = session(client)
    db.add(ReferenceAutorisation(reference="TEST-FAB-002", nom="Autre laboratoire", type=TypeStructure.fabricant))
    db.commit()
    autre = inscrire_structure(client, "fabricant", "TEST-FAB-002", "labo2")
    r = composer(client, autre, "carton", [next(iter(images))])
    assert r.status_code == 403 and "pas ete serialisee par votre structure" in r.json()["detail"]


def test_une_boite_deja_expediee_ne_peut_plus_etre_mise_en_carton(client):
    images, fab = serialiser(client)
    serie = next(iter(images))
    assert client.post("/evenements", headers=fab, data={"typeOperation": "expedition", "numeroSerie": serie}).status_code == 201
    r = composer(client, fab, "carton", [serie])
    assert r.status_code == 409 and "deja entree dans le circuit" in r.json()["detail"]


def test_un_carton_ouvert_ne_va_pas_sur_une_palette(client):
    images, fab = serialiser(client)
    c = composer(client, fab, "carton", [next(iter(images))]).json()["sscc"]
    db = session(client)
    db.get(Conteneur, c).etat = EtatConteneur.desagrege
    db.commit()
    r = composer(client, fab, "palette", [c])
    assert r.status_code == 409 and "ouvert" in r.json()["detail"]


def test_consulter_un_conteneur(client):
    images, fab = serialiser(client, quantite=2)
    c = composer(client, fab, "carton", list(images)).json()["sscc"]
    r = client.get(f"/conteneurs/{c}", headers=fab)
    assert r.status_code == 200 and r.json()["nombreBoites"] == 2
    assert client.get("/conteneurs/000000000000000000", headers=fab).status_code == 404
    assert client.get(f"/conteneurs/{c}").status_code == 401


def test_l_etiquette_est_un_datamatrix_gs1_du_sscc(client):
    images, fab = serialiser(client)
    c = composer(client, fab, "carton", [next(iter(images))]).json()["sscc"]
    r = client.get(f"/conteneurs/{c}/etiquette", headers=fab)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert lire_code(r.content) == f"(00){c}"


def test_la_base_refuse_une_boite_dans_deux_cartons_actifs(client):
    """Meme si le code de l'API se trompait, la base ne laisse pas une boite dans deux cartons."""
    import pytest
    from sqlalchemy.exc import IntegrityError
    images, fab = serialiser(client, quantite=2)
    serie = next(iter(images))
    c1 = composer(client, fab, "carton", [serie]).json()["sscc"]
    c2 = composer(client, fab, "carton", [s for s in images if s != serie]).json()["sscc"]
    db = session(client)
    db.add(Contenu(parent_sscc=c2, enfant_unite=serie))
    with pytest.raises(IntegrityError):
        db.commit()


def test_un_contenu_a_un_seul_enfant(client):
    import pytest
    from sqlalchemy.exc import IntegrityError
    images, fab = serialiser(client)
    c = composer(client, fab, "carton", [next(iter(images))]).json()["sscc"]
    db = session(client)
    db.add(Contenu(parent_sscc=c))   # ni boite ni carton
    with pytest.raises(IntegrityError):
        db.commit()


# ---------- Etape 2: scanner un carton ou une palette ----------

def evenements(client):
    from app.domaine.models import Evenement
    return session(client).query(Evenement).all()


def circuit(client, quantite=3):
    """Un fabricant serialise, met les boites dans un carton; renvoie (images, fabricant, sscc du carton)."""
    images, fab = serialiser(client, quantite=quantite)
    sscc = composer(client, fab, "carton", list(images)).json()["sscc"]
    return images, fab, sscc


def operer(client, entete, type_, sscc, **plus):
    return client.post("/conteneurs/evenements", headers=entete, data={"typeOperation": type_, "sscc": sscc, **plus})


def test_expedier_un_carton_enregistre_toutes_ses_boites(client):
    images, fab, sscc = circuit(client, quantite=3)
    r = operer(client, fab, "expedition", sscc, latitude="14.69", longitude="-17.44")
    assert r.status_code == 201
    c = r.json()
    assert c["nombreBoites"] == 3 and c["nombreAlertes"] == 0 and c["alerte"] is False
    assert c["dateHeure"] and c["latitude"] == 14.69 and c["longitude"] == -17.44
    evs = evenements(client)
    assert len(evs) == 3 and {e.numeroSerie for e in evs} == set(images)
    assert all(e.typeOperation.value == "expedition" and e.latitude == 14.69 for e in evs)


def test_le_grossiste_recoit_le_carton_d_un_seul_scan(client):
    images, fab, sscc = circuit(client)
    operer(client, fab, "expedition", sscc)
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    r = operer(client, gros, "reception", sscc)
    assert r.status_code == 201 and r.json()["nombreBoites"] == 3 and r.json()["nombreAlertes"] == 0
    # le carton est maintenant chez le grossiste
    assert client.get(f"/conteneurs/{sscc}", headers=gros).json()["structure"] == "Structure gros1"


def test_un_carton_peut_aller_directement_du_fabricant_a_l_officine(client):
    images, fab, sscc = circuit(client)
    operer(client, fab, "expedition", sscc)
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    r = operer(client, officine, "reception", sscc)
    assert r.status_code == 201 and r.json()["nombreAlertes"] == 0


def test_reception_sans_expedition_leve_une_alerte_par_boite(client):
    images, fab, sscc = circuit(client, quantite=2)
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    r = operer(client, gros, "reception", sscc)
    assert r.status_code == 201
    assert r.json()["nombreAlertes"] == 2 and r.json()["alerte"] is True
    from app.domaine.models import Anomalie
    anomalies = session(client).query(Anomalie).all()
    assert len(anomalies) == 2 and {a.typeAnomalie.value for a in anomalies} == {"ruptureSequence"}


def test_scanner_une_palette_enregistre_les_boites_de_tous_ses_cartons(client):
    images, fab = serialiser(client, quantite=4)
    series = list(images)
    a = composer(client, fab, "carton", series[:2]).json()["sscc"]
    b = composer(client, fab, "carton", series[2:]).json()["sscc"]
    p = composer(client, fab, "palette", [a, b]).json()["sscc"]
    r = operer(client, fab, "expedition", p)
    assert r.status_code == 201 and r.json()["nombreBoites"] == 4 and r.json()["niveau"] == "palette"
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    assert operer(client, gros, "reception", p).json()["nombreAlertes"] == 0
    # la palette et ses cartons sont chez le grossiste
    assert client.get(f"/conteneurs/{a}", headers=gros).json()["structure"] == "Structure gros1"
    assert client.get(f"/conteneurs/{b}", headers=gros).json()["structure"] == "Structure gros1"


def test_un_envoi_repete_ne_cree_pas_de_doublon(client):
    images, fab, sscc = circuit(client)
    ident = "operation-carton-0001"
    r1 = operer(client, fab, "expedition", sscc, identifiantClient=ident)
    r2 = operer(client, fab, "expedition", sscc, identifiantClient=ident)
    assert r1.status_code == 201 and r2.status_code == 200
    assert r2.json()["nombreBoites"] == 3
    assert len(evenements(client)) == 3


def test_les_roles_sont_ceux_des_boites(client):
    images, fab, sscc = circuit(client)
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    assert operer(client, officine, "expedition", sscc).status_code == 403     # l'officine ne fait que recevoir
    assert operer(client, fab, "reception", sscc).status_code == 403           # le fabricant ne fait qu'expedier
    assert operer(client, fab, "dispensation", sscc).status_code == 422        # pas de dispensation par carton
    assert len(evenements(client)) == 0


def test_conteneur_inconnu_ou_sans_code(client):
    images, fab, sscc = circuit(client)
    assert operer(client, fab, "expedition", "000000000000000000").status_code == 404
    r = client.post("/conteneurs/evenements", headers=fab, data={"typeOperation": "expedition"})
    assert r.status_code == 422


def test_un_carton_ouvert_se_scanne_boite_par_boite(client):
    images, fab, sscc = circuit(client)
    db = session(client)
    db.get(Conteneur, sscc).etat = EtatConteneur.desagrege
    db.commit()
    r = operer(client, fab, "expedition", sscc)
    assert r.status_code == 409 and "ouvert" in r.json()["detail"]


def test_expedier_avec_l_image_de_l_etiquette(client):
    images, fab, sscc = circuit(client)
    png = client.get(f"/conteneurs/{sscc}/etiquette", headers=fab).content
    r = client.post("/conteneurs/evenements", headers=fab, data={"typeOperation": "expedition"},
                    files={"image": ("carton.png", png, "image/png")})
    assert r.status_code == 201 and r.json()["sscc"] == sscc and r.json()["nombreBoites"] == 3
    assert r.json()["methodeLecture"] in ("classique", "deep_learning")


# ---------- Etape 3: ouvrir un carton, boite hors carton, carton incomplet ----------

def ouvrir_c(client, entete, sscc, presentes=None):
    corps = {} if presentes is None else {"presentes": presentes}
    return client.post(f"/conteneurs/{sscc}/ouvrir", headers=entete, json=corps)


def anomalies(client):
    from app.domaine.models import Anomalie
    return [a.typeAnomalie.value for a in session(client).query(Anomalie).all()]


def carton_chez_le_grossiste(client, quantite=3):
    images, fab, sscc = circuit(client, quantite=quantite)
    operer(client, fab, "expedition", sscc)
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    operer(client, gros, "reception", sscc)
    return images, fab, sscc, gros


def test_ouvrir_un_carton_libere_ses_boites_et_garde_l_historique(client):
    images, fab, sscc, gros = carton_chez_le_grossiste(client)
    r = ouvrir_c(client, gros, sscc)
    assert r.status_code == 200
    assert r.json()["elementsLiberes"] == 3 and r.json()["alerte"] is False and r.json()["manquants"] == []
    assert client.get(f"/conteneurs/{sscc}", headers=gros).json()["etat"] == "desagrege"
    assert client.get(f"/conteneurs/{sscc}", headers=gros).json()["nombreBoites"] == 0
    db = session(client)
    assert db.query(Contenu).count() == 3 and all(l.dateRetrait is not None for l in db.query(Contenu))


def test_une_boite_d_un_carton_ouvert_se_scanne_seule_sans_alerte(client):
    images, fab, sscc, gros = carton_chez_le_grossiste(client)
    ouvrir_c(client, gros, sscc)
    serie = next(iter(images))
    r = client.post("/evenements", headers=gros, data={"typeOperation": "expedition", "numeroSerie": serie})
    assert r.status_code == 201 and r.json()["alerte"] is False


def test_une_boite_scannee_seule_dans_un_carton_non_ouvert_leve_une_alerte(client):
    images, fab, sscc, gros = carton_chez_le_grossiste(client)
    serie = next(iter(images))
    r = client.post("/evenements", headers=gros, data={"typeOperation": "expedition", "numeroSerie": serie})
    assert r.status_code == 201
    assert r.json()["alerte"] is True and r.json()["typeAnomalie"] == "boiteHorsCarton"
    assert "ouvrez le carton" in r.json()["message"]
    assert anomalies(client).count("boiteHorsCarton") == 1


def test_la_dispensation_d_une_boite_dans_un_carton_non_ouvert_leve_une_alerte(client):
    images, fab, sscc = circuit(client, quantite=2)
    operer(client, fab, "expedition", sscc)
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    operer(client, officine, "reception", sscc)
    a, b = list(images)
    r = client.post("/dispensations", headers=officine, data={"numeroSerie": a})
    assert r.status_code == 201 and r.json()["alerte"] is True and r.json()["typeAnomalie"] == "boiteHorsCarton"
    ouvrir_c(client, officine, sscc)
    r2 = client.post("/dispensations", headers=officine, data={"numeroSerie": b})
    assert r2.status_code == 201 and r2.json()["alerte"] is False


def test_seule_la_structure_qui_detient_le_carton_l_ouvre(client):
    images, fab, sscc, gros = carton_chez_le_grossiste(client)
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    r = ouvrir_c(client, officine, sscc)
    assert r.status_code == 403 and "pas chez vous" in r.json()["detail"]
    assert ouvrir_c(client, fab, sscc).status_code == 403    # le fabricant l'a expedie: il ne le detient plus
    assert client.get(f"/conteneurs/{sscc}", headers=gros).json()["etat"] == "actif"


def test_un_carton_ne_s_ouvre_qu_une_fois(client):
    images, fab, sscc, gros = carton_chez_le_grossiste(client)
    assert ouvrir_c(client, gros, sscc).status_code == 200
    r = ouvrir_c(client, gros, sscc)
    assert r.status_code == 409 and "deja ouvert" in r.json()["detail"]


def test_carton_incomplet_a_l_ouverture(client):
    images, fab, sscc, gros = carton_chez_le_grossiste(client, quantite=3)
    series = list(images)
    r = ouvrir_c(client, gros, sscc, presentes=series[:2])
    assert r.status_code == 200
    c = r.json()
    assert c["alerte"] is True and c["manquants"] == [series[2]] and c["nombreAlertes"] == 1
    assert "1 manquant" in c["message"]
    assert anomalies(client) == ["cartonIncomplet"]


def test_un_element_etranger_a_la_liste_des_presentes_est_refuse(client):
    images, fab, sscc, gros = carton_chez_le_grossiste(client)
    r = ouvrir_c(client, gros, sscc, presentes=["ZZZZZZZZZZZZ"])
    assert r.status_code == 422
    assert client.get(f"/conteneurs/{sscc}", headers=gros).json()["etat"] == "actif"   # rien n'a change


def test_un_carton_sur_une_palette_s_ouvre_apres_la_palette(client):
    images, fab = serialiser(client, quantite=4)
    series = list(images)
    a = composer(client, fab, "carton", series[:2]).json()["sscc"]
    b = composer(client, fab, "carton", series[2:]).json()["sscc"]
    p = composer(client, fab, "palette", [a, b]).json()["sscc"]
    operer(client, fab, "expedition", p)
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    operer(client, gros, "reception", p)
    r = ouvrir_c(client, gros, a)
    assert r.status_code == 409 and "ouvrez d'abord la palette" in r.json()["detail"]
    assert ouvrir_c(client, gros, p).json()["elementsLiberes"] == 2
    # les cartons sont maintenant seuls et toujours fermes
    assert client.get(f"/conteneurs/{a}", headers=gros).json()["etat"] == "actif"
    assert ouvrir_c(client, gros, a).json()["elementsLiberes"] == 2


def test_palette_incomplete_signale_toutes_les_boites_du_carton_manquant(client):
    images, fab = serialiser(client, quantite=4)
    series = list(images)
    a = composer(client, fab, "carton", series[:2]).json()["sscc"]
    b = composer(client, fab, "carton", series[2:]).json()["sscc"]
    p = composer(client, fab, "palette", [a, b]).json()["sscc"]
    operer(client, fab, "expedition", p)
    gros = inscrire_structure(client, "grossisteRepartiteur", "TEST-GRO-001", "gros1")
    operer(client, gros, "reception", p)
    r = ouvrir_c(client, gros, p, presentes=[a])
    assert r.json()["manquants"] == [b] and r.json()["nombreAlertes"] == 2
    assert anomalies(client).count("cartonIncomplet") == 2


def test_ouvrir_un_conteneur_inconnu_ou_sans_connexion(client):
    images, fab, sscc = circuit(client)
    assert ouvrir_c(client, fab, "000000000000000000").status_code == 404
    assert client.post(f"/conteneurs/{sscc}/ouvrir", json={}).status_code == 401


# ---------- Etape 4: lecture d'un conteneur pour l'application mobile ----------

def test_lire_un_conteneur_par_sscc_et_savoir_s_il_est_chez_soi(client):
    images, fab, sscc = circuit(client, quantite=2)
    r = client.post("/conteneurs/lecture", headers=fab, data={"sscc": sscc})
    assert r.status_code == 200
    c = r.json()
    assert c["sscc"] == sscc and c["nombreBoites"] == 2 and c["chezVous"] is True and c["etat"] == "actif"
    assert c["methodeLecture"] == "saisie"
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    assert client.post("/conteneurs/lecture", headers=officine, data={"sscc": sscc}).json()["chezVous"] is False


def test_lire_un_conteneur_par_image_de_l_etiquette(client):
    images, fab, sscc = circuit(client)
    png = client.get(f"/conteneurs/{sscc}/etiquette", headers=fab).content
    r = client.post("/conteneurs/lecture", headers=fab, files={"image": ("carton.png", png, "image/png")})
    assert r.status_code == 200 and r.json()["sscc"] == sscc
    assert r.json()["methodeLecture"] in ("classique", "deep_learning")


def test_lire_un_conteneur_inconnu_ou_sans_code(client):
    images, fab, sscc = circuit(client)
    assert client.post("/conteneurs/lecture", headers=fab, data={"sscc": "000000000000000000"}).status_code == 404
    assert client.post("/conteneurs/lecture", headers=fab).status_code == 422
    assert client.post("/conteneurs/lecture", data={"sscc": sscc}).status_code == 401


def test_le_carton_chez_le_grossiste_apres_reception_est_chez_lui(client):
    images, fab, sscc, gros = carton_chez_le_grossiste(client)
    assert client.post("/conteneurs/lecture", headers=gros, data={"sscc": sscc}).json()["chezVous"] is True
    assert client.post("/conteneurs/lecture", headers=fab, data={"sscc": sscc}).json()["chezVous"] is False
