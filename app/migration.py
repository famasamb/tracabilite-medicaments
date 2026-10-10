"""Mise a niveau automatique d'une base existante (ajout des colonnes apparues apres sa creation)."""
from sqlalchemy import inspect, text

from .db import Base


def mettre_a_niveau(moteur) -> None:
    """Cree les tables manquantes, puis ajoute les colonnes et index recents (utilisateurs, evenements)."""
    Base.metadata.create_all(moteur)
    colonnes = {c["name"] for c in inspect(moteur).get_columns("utilisateurs")}
    with moteur.begin() as connexion:
        if "email" not in colonnes:
            connexion.execute(text("ALTER TABLE utilisateurs ADD COLUMN email VARCHAR(254)"))
        if "versionSession" not in colonnes:
            connexion.execute(text('ALTER TABLE utilisateurs ADD COLUMN "versionSession" INTEGER NOT NULL DEFAULT 0'))
        connexion.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_utilisateurs_email ON utilisateurs (email)"))
    # Operations faites sans reseau: identifiant fabrique par le telephone, unique pour chaque utilisateur
    colonnes_evenements = {c["name"] for c in inspect(moteur).get_columns("evenements")}
    with moteur.begin() as connexion:
        if "identifiantClient" not in colonnes_evenements:
            connexion.execute(text('ALTER TABLE evenements ADD COLUMN "identifiantClient" VARCHAR(64)'))
        connexion.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_evenement_client ON evenements (utilisateur_id, "identifiantClient")'))
