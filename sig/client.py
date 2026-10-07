"""Acces de l'application SIG a l'API de tracabilite (fiche 1: s'authentifier; fiche 10: tableau de bord).

L'application SIG n'a pas d'acces direct a la base: tout passe par l'API, avec le compte d'un utilisateur de
la PNA. Le client recoit un `httpx.Client`, ce qui permet de le tester sans serveur."""
from datetime import date

import httpx


class ErreurAPI(Exception):
    """Une erreur a montrer telle quelle a la personne qui utilise l'application."""

    def __init__(self, message: str, statut: int | None = None):
        super().__init__(message)
        self.message, self.statut = message, statut


def _message(reponse: httpx.Response) -> str:
    try:
        detail = reponse.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail:            # erreur de validation: liste de details
        return "; ".join(str(d.get("msg", d)) for d in detail)
    return f"Erreur {reponse.status_code}."


class ClientAPI:
    def __init__(self, http: httpx.Client):
        self.http = http

    @classmethod
    def vers(cls, adresse: str) -> "ClientAPI":
        return cls(httpx.Client(base_url=adresse.rstrip("/"), timeout=30))

    def _requete(self, methode: str, chemin: str, **kw) -> httpx.Response:
        try:
            reponse = self.http.request(methode, chemin, **kw)
        except httpx.TransportError:
            raise ErreurAPI("Impossible de joindre l'API. Verifiez l'adresse et que le serveur est demarre.") from None
        if reponse.status_code >= 400:
            raise ErreurAPI(_message(reponse), reponse.status_code)
        return reponse

    def connecter(self, identifiant: str, mot_de_passe: str) -> dict:
        """Ouvre une session et renvoie le profil. Refuse un compte qui n'est pas celui d'une PNA."""
        jeton = self._requete("POST", "/auth/connexion",
                              data={"username": identifiant, "password": mot_de_passe}).json()["access_token"]
        self.http.headers["Authorization"] = f"Bearer {jeton}"
        profil = self._requete("GET", "/auth/moi").json()
        if profil["structure_type"] != "PNA":
            self.http.headers.pop("Authorization", None)
            raise ErreurAPI("Cette application est reservee aux utilisateurs de la PNA.", 403)
        return profil

    def liste_sr(self) -> list[dict]:
        return self._requete("GET", "/sr").json()

    def tableau(self, sr_id: str | None = None, du: date | None = None, au: date | None = None) -> dict:
        parametres = {}
        if sr_id:
            parametres["sr_id"] = sr_id
        if du:
            parametres["du"] = du.isoformat()
        if au:
            parametres["au"] = au.isoformat()
        return self._requete("GET", "/tableau-de-bord", params=parametres).json()