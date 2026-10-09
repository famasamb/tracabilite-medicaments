"""Blocage apres des echecs de connexion et en-tetes de securite."""


def _echecs(client, n, identifiant="awa.diop", mdp="Mauvais123456"):
    return [client.post("/auth/connexion", data={"username": identifiant, "password": mdp}).status_code
            for _ in range(n)]


def test_apres_cinq_echecs_la_connexion_est_bloquee(client):
    from tests.test_auth import inscrire, se_connecter
    inscrire(client)
    assert _echecs(client, 5) == [401] * 5
    r = se_connecter(client)                       # meme avec le bon mot de passe
    assert r.status_code == 429 and "Reessayez dans" in r.json()["detail"]
    assert int(r.headers["retry-after"]) > 0


def test_quatre_echecs_ne_bloquent_pas(client):
    from tests.test_auth import inscrire, se_connecter
    inscrire(client)
    _echecs(client, 4)
    assert se_connecter(client).status_code == 200


def test_une_connexion_reussie_remet_le_compteur_a_zero(client):
    from tests.test_auth import inscrire, se_connecter
    inscrire(client)
    _echecs(client, 4)
    assert se_connecter(client).status_code == 200
    assert _echecs(client, 4) == [401] * 4
    assert se_connecter(client).status_code == 200


def test_le_blocage_ne_touche_pas_les_autres_comptes(client):
    from tests.test_auth import inscrire, se_connecter
    inscrire(client)
    _echecs(client, 5)
    assert _echecs(client, 1, identifiant="autre.personne") == [401]


def test_le_blocage_prend_fin_apres_quinze_minutes(client, monkeypatch):
    from datetime import timedelta
    from app import routes_auth
    from tests.test_auth import inscrire, se_connecter
    inscrire(client)
    _echecs(client, 5)
    assert se_connecter(client).status_code == 429
    avant = routes_auth.maintenant
    monkeypatch.setattr(routes_auth, "maintenant", lambda: avant() + timedelta(minutes=16))
    assert se_connecter(client).status_code == 200


def test_identifiant_inconnu_aussi_compte_les_echecs(client):
    assert _echecs(client, 5, identifiant="fantome") == [401] * 5
    assert _echecs(client, 1, identifiant="FANTOME") == [429]


def test_en_tetes_de_securite(client):
    r = client.get("/sante")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "camera=(self)" in r.headers["permissions-policy"]
    assert "content-security-policy" not in r.headers            # reservee a l'application mobile


def test_politique_de_contenu_de_l_application_mobile(client):
    r = client.get("/mobile/")
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
