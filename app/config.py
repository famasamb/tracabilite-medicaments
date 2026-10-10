"""Configuration par fichier .env (a la racine du projet), sans bibliotheque supplementaire.

Format: une ligne NOM=valeur (guillemets facultatifs), les lignes commencant par # sont ignorees.
Une variable deja definie dans l'environnement n'est jamais ecrasee par le fichier.
Le fichier .env contient des secrets: il ne doit jamais etre ajoute a Git.
"""
import os
from pathlib import Path


def charger_env(chemin: Path | None = None) -> int:
    """Charge le fichier .env s'il existe; renvoie le nombre de variables ajoutees."""
    if os.getenv("TRACABILITE_SANS_ENV"):
        return 0
    chemin = chemin or Path.cwd() / ".env"
    if not chemin.is_file():
        return 0
    ajoutees = 0
    for ligne in chemin.read_text(encoding="utf-8-sig").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        nom, valeur = ligne.split("=", 1)
        nom, valeur = nom.strip(), valeur.strip()
        if len(valeur) >= 2 and valeur[0] == valeur[-1] and valeur[0] in "\"'":
            valeur = valeur[1:-1]
        if nom and nom not in os.environ:
            os.environ[nom] = valeur
            ajoutees += 1
    return ajoutees
