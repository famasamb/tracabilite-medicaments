"""Mot de passe oublie: lien par e-mail, usage unique, expiration, sessions, migration."""
import re
from datetime import timedelta

from sqlalchemy import create_engine, inspect, text

from app.db import Base, get_db
from app.main import app as application
from app.migration import mettre_a_niveau
from app.models import JetonReinitialisation, Utilisateur, maintenant
from tests.test_auth import inscrire, se_connecter

EMAIL = "awa.diop@essai.sn"


def jeton_du_dernier_courriel(courriels):
    return re.search(r"/mobile/#/reinitialiser/([\w-]+)", courriels[-1]["texte"]).group(1)


def demander(client, email=EMAIL):
    return client.post("/auth/mot-de-passe-oublie", json={"email": email})


def reinitialiser(client, jeton, mdp="NouveauSecret77"):
    return client.post("/auth/reinitialiser-mot-de-passe", json={"jeton": jeton, "nouveauMotDePasse": mdp})


def base_de_test():
    return next(application.dependency_overrides[get_db]())


def test_la_reponse_est_identique_que_l_adresse_existe_ou_non(client, courriels):
    inscrire(client)
    connue, inconnue = demander(client), demander(client, "personne@essai.sn")
    assert connue.status_code == inconnue.status_code == 200
    assert connue.json() == inconnue.json()
    assert [c["a"] for c in courriels] == [EMAIL]          # rien n'est envoye a l'adresse inconnue


def test_reinitialisation_complete(client, courriels):
    inscrire(client)
    demander(client)
    assert "Reinitialisation" in courriels[-1]["sujet"] and "30 minutes" in courriels[-1]["texte"]
    assert reinitialiser(client, jeton_du_dernier_courriel(courriels)).status_code == 200
    assert se_connecter(client, mdp="MotDePasse2026").status_code == 401
    assert se_connecter(client, mdp="NouveauSecret77").status_code == 200
    assert "modifie" in courriels[-1]["sujet"]             # courriel d'alerte apres le changement


def test_le_lien_ne_sert_qu_une_fois(client, courriels):
    inscrire(client)
    demander(client)
    jeton = jeton_du_dernier_courriel(courriels)
    assert reinitialiser(client, jeton).status_code == 200
    assert reinitialiser(client, jeton, "AutreSecret999").status_code == 400
    assert se_connecter(client, mdp="NouveauSecret77").status_code == 200


def test_un_lien_expire_est_refuse(client, courriels):
    inscrire(client)
    demander(client)
    db = base_de_test()
    for t in db.query(JetonReinitialisation):
        t.expireLe = maintenant() - timedelta(minutes=1)
    db.commit()
    assert reinitialiser(client, jeton_du_dernier_courriel(courriels)).status_code == 400
    assert se_connecter(client, mdp="MotDePasse2026").status_code == 200


def test_un_jeton_invente_est_refuse(client):
    inscrire(client)
    assert reinitialiser(client, "x" * 43).status_code == 400


def test_une_nouvelle_demande_invalide_l_ancien_lien(client, courriels):
    inscrire(client)
    demander(client)
    premier = jeton_du_dernier_courriel(courriels)
    demander(client)
    second = jeton_du_dernier_courriel(courriels)
    assert premier != second
    assert reinitialiser(client, premier).status_code == 400
    assert reinitialiser(client, second).status_code == 200


def test_trois_demandes_par_heure_au_maximum(client, courriels):
    inscrire(client)
    for _ in range(5):
        assert demander(client).status_code == 200
    assert len(courriels) == 3


def test_le_jeton_n_est_jamais_stocke_en_clair(client, courriels):
    inscrire(client)
    demander(client)
    jeton = jeton_du_dernier_courriel(courriels)
    assert all(jeton not in t.empreinte and len(t.empreinte) == 64 for t in base_de_test().query(JetonReinitialisation))


def test_mot_de_passe_trop_court_refuse_et_lien_conserve(client, courriels):
    inscrire(client)
    demander(client)
    jeton = jeton_du_dernier_courriel(courriels)
    assert reinitialiser(client, jeton, "court").status_code == 422
    assert reinitialiser(client, jeton).status_code == 200


def test_les_sessions_ouvertes_sont_fermees_apres_une_reinitialisation(client, courriels):
    inscrire(client)
    ancien = se_connecter(client).json()["access_token"]
    entete = {"Authorization": f"Bearer {ancien}"}
    assert client.get("/auth/moi", headers=entete).status_code == 200
    demander(client)
    reinitialiser(client, jeton_du_dernier_courriel(courriels))
    assert client.get("/auth/moi", headers=entete).status_code == 401


def test_changer_son_mot_de_passe_ferme_les_autres_sessions_mais_garde_la_courante(client, courriels):
    inscrire(client)
    autre_appareil = {"Authorization": "Bearer " + se_connecter(client).json()["access_token"]}
    courante = {"Authorization": "Bearer " + se_connecter(client).json()["access_token"]}
    r = client.post("/auth/mot-de-passe", headers=courante,
                    json={"motDePasseActuel": "MotDePasse2026", "nouveauMotDePasse": "NouveauSecret77"})
    assert r.status_code == 200
    assert client.get("/auth/moi", headers=autre_appareil).status_code == 401
    assert client.get("/auth/moi", headers=courante).status_code == 401
    assert client.get("/auth/moi", headers={"Authorization": "Bearer " + r.json()["access_token"]}).status_code == 200
    assert "modifie" in courriels[-1]["sujet"]


def test_adresse_invalide_ou_deja_utilisee_refusee_a_l_inscription(client):
    inscrire(client)
    corps = {"structure": {"nom": "Autre Grossiste", "type": "grossisteRepartiteur", "localisation": "Dakar",
                           "referenceAutorisation": "TEST-GRO-001"},
             "responsable": {"nom": "Ibrahima Sow", "fonction": "Pharmacien", "identifiantConnexion": "labo2",
                             "email": EMAIL.upper(), "motDePasse": "MotDePasse2026"}}
    assert client.post("/structures/inscription", json=corps).status_code == 409   # casse ignoree
    corps["responsable"]["email"] = "pas-une-adresse"
    assert client.post("/structures/inscription", json=corps).status_code == 422


def test_l_adresse_est_enregistree_en_minuscules_et_visible_dans_le_profil(client):
    inscrire(client)
    jeton = se_connecter(client).json()["access_token"]
    assert client.get("/auth/moi", headers={"Authorization": f"Bearer {jeton}"}).json()["email"] == EMAIL


def test_modifier_son_adresse(client, courriels):
    inscrire(client)
    entete = {"Authorization": "Bearer " + se_connecter(client).json()["access_token"]}
    corps = {"motDePasseActuel": "MotDePasse2026", "email": "Nouvelle.Adresse@Essai.sn"}
    assert client.put("/auth/courriel", headers=entete, json=dict(corps, motDePasseActuel="Faux123456")).status_code == 400
    assert client.put("/auth/courriel", headers=entete, json=corps).json()["email"] == "nouvelle.adresse@essai.sn"
    demander(client, "nouvelle.adresse@essai.sn")
    assert courriels[-1]["a"] == "nouvelle.adresse@essai.sn"


def test_modifier_son_adresse_refuse_une_adresse_d_un_autre_compte(client):
    inscrire(client)
    client.post("/structures/inscription", json={
        "structure": {"nom": "Pharmacie B", "type": "officine", "localisation": "Thies", "referenceAutorisation": "TEST-OFF-001"},
        "responsable": {"nom": "Awa B", "fonction": "Pharmacien", "identifiantConnexion": "pharma.b",
                        "email": "b@essai.sn", "motDePasse": "MotDePasse2026"}})
    entete = {"Authorization": "Bearer " + se_connecter(client, "pharma.b").json()["access_token"]}
    r = client.put("/auth/courriel", headers=entete, json={"motDePasseActuel": "MotDePasse2026", "email": EMAIL})
    assert r.status_code == 409


def test_demande_sans_adresse_valide_refusee(client):
    assert demander(client, "n-importe-quoi").status_code == 422


def test_migration_d_une_ancienne_base_sans_perdre_les_comptes():
    moteur = create_engine("sqlite://")
    Base.metadata.create_all(moteur)
    with moteur.begin() as c:
        c.execute(text("DROP INDEX uq_utilisateurs_email"))
        c.execute(text("ALTER TABLE utilisateurs DROP COLUMN email"))
        c.execute(text('ALTER TABLE utilisateurs DROP COLUMN "versionSession"'))
        c.execute(text("DROP TABLE jetons_reinitialisation"))
        c.execute(text("INSERT INTO structures (id, nom, type, localisation) VALUES ('s1','Labo','fabricant','Dakar')"))
        c.execute(text("INSERT INTO utilisateurs (id, nom, fonction, \"identifiantConnexion\", \"motDePasse\", role, structure_id) "
                       "VALUES ('u1','Awa','Chef','awa','hash','responsable','s1')"))
    assert "email" not in {c["name"] for c in inspect(moteur).get_columns("utilisateurs")}
    mettre_a_niveau(moteur)
    mettre_a_niveau(moteur)   # sans danger si on le relance
    colonnes = {c["name"] for c in inspect(moteur).get_columns("utilisateurs")}
    assert {"email", "versionSession"} <= colonnes and "jetons_reinitialisation" in inspect(moteur).get_table_names()
    with moteur.connect() as c:
        assert c.execute(text('SELECT "identifiantConnexion", email, "versionSession" FROM utilisateurs')).one() == ("awa", None, 0)


# ---------- Envoi reel (SMTP simule) ----------
from app import courriel as _courriel  # noqa: E402

ENVOYER_POUR_DE_VRAI = _courriel.envoyer   # la fixture automatique remplace la fonction pendant les tests


class FauxSMTP:
    appels = []

    def __init__(self, hote, port, timeout=None, context=None):
        FauxSMTP.appels.append(("connexion", hote, port))

    def __enter__(self): return self
    def __exit__(self, *a): return False
    def starttls(self, context=None): FauxSMTP.appels.append(("starttls",))
    def login(self, u, m): FauxSMTP.appels.append(("login", u, m))
    def send_message(self, message): FauxSMTP.appels.append(("message", message["To"], message["Subject"], message.get_content()))


def test_envoi_smtp_avec_chiffrement_et_identifiants(monkeypatch):
    FauxSMTP.appels = []
    monkeypatch.setattr("smtplib.SMTP", FauxSMTP)
    for nom, valeur in {"SMTP_HOTE": "smtp.exemple.sn", "SMTP_PORT": "587", "SMTP_UTILISATEUR": "noreply@exemple.sn",
                        "SMTP_MOT_DE_PASSE": "secret"}.items():
        monkeypatch.setenv(nom, valeur)
    ENVOYER_POUR_DE_VRAI("awa@essai.sn", "Sujet", "Corps du message")
    assert [a[0] for a in FauxSMTP.appels] == ["connexion", "starttls", "login", "message"]
    assert FauxSMTP.appels[-1][1:3] == ("awa@essai.sn", "Sujet")


def test_un_echec_d_envoi_ne_leve_pas_d_exception(monkeypatch):
    def echec(*a, **k): raise OSError("serveur injoignable")
    monkeypatch.setattr("smtplib.SMTP", echec)
    monkeypatch.setenv("SMTP_HOTE", "smtp.exemple.sn")
    ENVOYER_POUR_DE_VRAI("awa@essai.sn", "Sujet", "Corps")   # ne doit pas planter


def test_sans_configuration_le_courriel_est_affiche_dans_la_console(monkeypatch, capsys):
    monkeypatch.delenv("SMTP_HOTE", raising=False)
    ENVOYER_POUR_DE_VRAI("awa@essai.sn", "Sujet", "Lien: http://exemple")
    assert "COURRIEL NON ENVOYE" in capsys.readouterr().out
