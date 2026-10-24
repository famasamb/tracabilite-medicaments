"""Erreur metier: une regle de l'application refuse l'operation.

Les services levent cette erreur sans rien savoir d'HTTP. La couche api la traduit en reponse
(le code est le statut HTTP, le message est le detail), voir app/main.py.
"""


class ErreurMetier(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
