"""Etape 30: planche de codes a imprimer pour prendre de vraies photos.

Les 12 codes sont des unites reelles du jeu de donnees (base donnees.db), 3 par produit.
Pour une evaluation honnete, on prend en priorite des codes du groupe TEST (repartition.csv): ceux que le modele
YOLO n'a jamais vus pendant l'entrainement ni la validation. S'il en manque pour un produit, on complete avec
le groupe validation puis apprentissage, et la liste affichee dit le groupe de chaque code.
Lancer depuis la racine du projet:  python -m jeu_de_donnees.generer_planche
"""
import csv
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
ORDRE_GROUPES = {"test": 0, "val": 1, "train": 2}


def groupes_yolo() -> dict[str, str]:
    """Numero de serie -> groupe (train, val, test) fixe par preparer_yolo; vide si le fichier n'existe pas."""
    chemin = DOSSIER / "repartition.csv"
    if not chemin.exists():
        return {}
    with open(chemin, newline="", encoding="utf-8") as f:
        return {l["numeroSerie"]: l["groupe"] for l in csv.DictReader(f)}


def main() -> None:
    if not (DOSSIER / "donnees.db").exists():
        raise SystemExit("Base du jeu de donnees absente: lancez d'abord generer_images_propres.")
    generateur = np.random.default_rng(GRAINE)
    groupes = groupes_yolo()
    codes = []
    with SessionLocal() as db:
        for produit in db.query(Produit).order_by(Produit.nom).all():
            unites = (db.query(Unite).join(Lot).filter(Lot.produit_id == produit.id)
                      .order_by(Unite.numeroSerie).all())
            # priorite aux codes du groupe test; a groupe egal, tirage reproductible
            melange = [unites[int(i)] for i in generateur.permutation(len(unites))]
            melange.sort(key=lambda u: ORDRE_GROUPES.get(groupes.get(u.numeroSerie), 3))
            for u in sorted(melange[:PAR_PRODUIT], key=lambda u: u.numeroSerie):
                contenu = construire_contenu(produit.gtin, produit.id, u.lot.numeroLot,
                                             u.lot.datePeremption, u.numeroSerie)
                codes.append((u.numeroSerie, contenu, produit.nom, u.lot.numeroLot, groupes.get(u.numeroSerie, "?")))
    page = composer_planche([c[:4] for c in codes])
    image = Image.fromarray(page)
    image.save(DOSSIER / "planche_a_imprimer.pdf", resolution=300.0)
    image.save(DOSSIER / "planche_a_imprimer.png", dpi=(300, 300))
    print(f"{len(codes)} codes places sur la planche:")
    for serie, _contenu, nom, lot, groupe in codes:
        print(f"  {serie}  {nom}  {lot}  (groupe {groupe})")
    # l'ordre des codes sur la planche (de gauche a droite, ligne par ligne) sert a ranger les photos
    with open(DOSSIER / "planche_codes.csv", "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.writer(f)
        ecrivain.writerow(["ordre", "numeroSerie", "produit", "lot", "groupe"])
        for ordre, (serie, _contenu, nom, lot, groupe) in enumerate(codes, start=1):
            ecrivain.writerow([ordre, serie, nom, lot, groupe])
    hors_test = [c[0] for c in codes if c[4] != "test"]
    if hors_test:
        print(f"Attention: {len(hors_test)} code(s) ne sont pas du groupe test: {', '.join(hors_test)}")
    print(f"Fichier a imprimer: {DOSSIER / 'planche_a_imprimer.pdf'}")


if __name__ == "__main__":
    main()
