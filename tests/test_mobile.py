"""Tests de l'application mobile: les pages sont bien servies par l'API, a la meme adresse."""
import json
import re

ADRESSE = "/mobile/"


def test_la_page_d_accueil_de_l_application_est_servie(client):
    r = client.get(ADRESSE)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert '<html lang="fr">' in r.text and "Traçabilité" in r.text and "viewport-fit=cover" in r.text


def test_l_adresse_sans_barre_finale_redirige_vers_l_application(client):
    r = client.get("/mobile", follow_redirects=True)
    assert r.status_code == 200 and "Traçabilité" in r.text


def test_tous_les_fichiers_cites_par_la_page_existent(client):
    page = client.get(ADRESSE).text
    chemins = set(re.findall(r'(?:href|src)="([^"#:]+)"', page))
    assert {"app.css", "app.js", "manifest.webmanifest"} <= chemins
    for chemin in chemins:
        assert client.get(ADRESSE + chemin).status_code == 200, chemin


def test_le_manifeste_decrit_une_application_installable(client):
    manifeste = json.loads(client.get(ADRESSE + "manifest.webmanifest").text)
    assert manifeste["start_url"] == "/mobile/" and manifeste["display"] == "standalone" and manifeste["lang"] == "fr"
    tailles = {i["sizes"] for i in manifeste["icons"]}
    assert {"192x192", "512x512"} <= tailles
    for icone in manifeste["icons"]:
        r = client.get(ADRESSE + icone["src"])
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_les_polices_sont_embarquees_pour_fonctionner_sans_reseau(client):
    css = client.get(ADRESSE + "app.css").text
    polices = re.findall(r'url\("([^"]+\.woff2)"\)', css)
    assert len(polices) == 5  # Bricolage Grotesque et Hanken Grotesk (4 graisses)
    for police in polices:
        assert client.get(ADRESSE + police).status_code == 200


def test_tout_ce_que_le_service_worker_met_en_cache_existe(client):
    sw = client.get(ADRESSE + "sw.js").text
    coque = re.search(r"const COQUE = \[(.*?)\];", sw, re.S).group(1)
    fichiers = re.findall(r'"([^"]+)"', coque)
    for fichier in fichiers:
        assert client.get(ADRESSE + fichier).status_code == 200, fichier


def test_le_service_worker_est_servi_et_l_api_n_est_pas_touchee(client):
    r = client.get(ADRESSE + "sw.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert client.get("/sante").json() == {"etat": "ok"}
    assert client.get("/mobile/inexistant.js").status_code == 404


def test_chaque_ecran_appele_par_l_application_est_defini(client):
    js = client.get(ADRESSE + "app.js").text
    definis = set(re.findall(r"function (vue\w+)\(", js))
    appeles = set(re.findall(r"\b(vue[A-Z]\w+)\(", js))
    assert appeles <= definis, appeles - definis


def test_les_references_d_essai_permettent_l_inscription(client, db):
    from app.references import charger_references
    assert charger_references(db, "data/references_essai.csv") == 4
    assert charger_references(db, "data/references_essai.csv") == 0
