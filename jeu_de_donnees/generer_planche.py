"""Etape 30: planche de codes a imprimer pour prendre de vraies photos.

Les 12 codes sont des unites reelles du jeu de donnees (base donnees.db), 3 par produit.
Lancer depuis la racine du projet:  python -m jeu_de_donnees.generer_planche
"""
import os
from pathlib import Path

DOSSIER = Path(__file__).parent
os.environ["DATABASE_URL"] = f"sqlite:///{(DOSSIER / 'donnees.db').as_posix()}"

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from app.codes import construire_contenu  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Lot, Produit, Unite  # noqa: E402

from .planche import composer_planche  # noqa: E402

GRAINE = 30
PAR_PRODUIT = 3


def main() -> None:
    if not (DOSSIER / "donnees.db").exists():
        raise SystemExit("Base du jeu de donnees absente: lancez d'abord generer_images_propres.")
    generateur = np.random.default_rng(GRAINE)
    codes = []
    with SessionLocal() as db:
        for produit in db.query(Produit).order_by(Produit.nom).all():
            unites = (db.query(Unite).join(Lot).filter(Lot.produit_id == produit.id)
                      .order_by(Unite.numeroSerie).all())
            for indice in sorted(generateur.choice(len(unites), PAR_PRODUIT, replace=False)):
                u = unites[int(indice)]
                contenu = construire_contenu(produit.gtin, produit.id, u.lot.numeroLot,
                                             u.lot.datePeremption, u.numeroSerie)
                codes.append((u.numeroSerie, contenu, produit.nom, u.lot.numeroLot))
    page = composer_planche(codes)
    image = Image.fromarray(page)
    image.save(DOSSIER / "planche_a_imprimer.pdf", resolution=300.0)
    image.save(DOSSIER / "planche_a_imprimer.png", dpi=(300, 300))
    print(f"{len(codes)} codes places sur la planche:")
    for serie, _contenu, nom, lot in codes:
        print(f"  {serie}  {nom}  {lot}")
    print(f"Fichier a imprimer: {DOSSIER / 'planche_a_imprimer.pdf'}")


if __name__ == "__main__":
    main()