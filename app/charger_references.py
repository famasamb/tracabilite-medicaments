"""Ajoute des references d'autorisation a la base, pour essayer l'inscription.

A lancer depuis la racine du projet:
    python -m app.charger_references data/references_essai.csv

Une reference deja presente n'est pas dupliquee.
"""
import sys

from .db import SessionLocal
from .references import charger_references


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.charger_references chemin_du_fichier.csv")
    with SessionLocal() as db:
        ajoutees = charger_references(db, sys.argv[1])
    print(f"{ajoutees} reference(s) ajoutee(s).")


if __name__ == "__main__":
    main()
