"""Etape 28: images propres du jeu de donnees (phase 3 de la methodologie).

Les codes viennent de la vraie chaine de l'application: inscription d'un fabricant, enregistrement
de produits, serialisation de lots. Les produits sont des produits de test. Rien n'est ecrit dans
tracabilite.db: tout va dans jeu_de_donnees/donnees.db.

Lancer depuis la racine du projet:  python -m jeu_de_donnees.generer_images_propres
"""
import csv
import io
import os
import shutil
import zipfile
from datetime import date
from pathlib import Path

DOSSIER = Path(__file__).parent
# La base du jeu de donnees est separee de la base de developpement.
# Il faut fixer cette variable AVANT d'importer l'application.
os.environ["DATABASE_URL"] = f"sqlite:///{(DOSSIER / 'donnees.db').as_posix()}"

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.codes import cle_de_controle_gtin, construire_contenu, lire_code  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Unite  # noqa: E402
from app.references import charger_references  # noqa: E402

from .composition import HAUTEUR, LARGEUR, composer_boite  # noqa: E402

GRAINE = 2026
MOT_DE_PASSE = "MotDePasseJeuDonnees1"
PRODUITS_TEST = [  # (nom, composition, forme, conditionnement, corps du GTIN sur 13 chiffres)
    ("Paracetamol 500 mg", "Paracetamol 500 mg", "Comprime", "Boite de 16", "0376000000101"),
    ("Amoxicilline 500 mg", "Amoxicilline 500 mg", "Gelule", "Boite de 12", "0376000000102"),
    ("Ibuprofene 400 mg", "Ibuprofene 400 mg", "Comprime", "Boite de 20", "0376000000103"),
    ("Metformine 850 mg", "Metformine 850 mg", "Comprime", "Boite de 30", "0376000000104"),
]
UNITES_PAR_LOT = 25
PEREMPTION = date(2028, 6, 30)


def main() -> None:
    (DOSSIER / "donnees.db").unlink(missing_ok=True)
    dossier_images = DOSSIER / "images" / "propres"
    shutil.rmtree(dossier_images, ignore_errors=True)
    dossier_images.mkdir(parents=True)
    generateur = np.random.default_rng(GRAINE)

    with TestClient(app) as client:   # le demarrage de l'API cree les tables
        with SessionLocal() as db:
            charger_references(db, "data/references_test.csv")
        r = client.post("/structures/inscription", json={
            "structure": {"nom": "Laboratoire Jeu de Donnees", "type": "fabricant",
                          "localisation": "Dakar", "referenceAutorisation": "TEST-FAB-001"},
            "responsable": {"nom": "Responsable Jeu", "fonction": "Pharmacien",
                            "identifiantConnexion": "labo.jeu", "email": "labo.jeu" + "@essai.sn", "motDePasse": MOT_DE_PASSE}})
        assert r.status_code == 201, r.text
        jeton = client.post("/auth/connexion", data={"username": "labo.jeu", "password": MOT_DE_PASSE})
        entete = {"Authorization": f"Bearer {jeton.json()['access_token']}"}

        images: dict[str, tuple[str, bytes]] = {}   # numero de serie -> (nom du produit, png)
        for i, (nom, compo, forme, cond, corps) in enumerate(PRODUITS_TEST, start=1):
            gtin = corps + str(cle_de_controle_gtin(corps))
            r = client.post("/produits", headers=entete, json={
                "nom": nom, "composition": compo, "formePharmaceutique": forme,
                "conditionnement": cond, "gtin": gtin})
            assert r.status_code == 201, r.text
            r = client.post("/lots/serialisation", headers=entete, json={
                "produit_id": r.json()["id"], "numeroLot": f"JD-{i:03d}",
                "quantite": UNITES_PAR_LOT, "datePeremption": PEREMPTION.isoformat()})
            assert r.status_code == 201, r.text
            with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
                for fichier in archive.namelist():
                    images[fichier[:-4]] = (nom, archive.read(fichier))

    lignes, lus = [], 0
    with SessionLocal() as db:
        for serie, (nom, png) in sorted(images.items()):
            unite = db.get(Unite, serie)
            lot, produit = unite.lot, unite.lot.produit
            attendu = construire_contenu(produit.gtin, produit.id, lot.numeroLot,
                                         lot.datePeremption, serie)
            image, (x, y, largeur, hauteur) = composer_boite(png, nom, lot.numeroLot, generateur)
            fichier = f"{serie}.png"
            cv2.imwrite(str(dossier_images / fichier), image)
            ok, relu = cv2.imencode(".png", image)
            lus += lire_code(relu.tobytes()) == attendu
            lignes.append({"fichier": f"propres/{fichier}", "numeroSerie": serie,
                           "contenuAttendu": attendu, "produit": nom, "gtin": produit.gtin,
                           "lot": lot.numeroLot, "source": "synthetique", "degradation": "aucune",
                           "niveau": 0, "x": x, "y": y, "largeur": largeur, "hauteur": hauteur,
                           "largeurImage": LARGEUR, "hauteurImage": HAUTEUR})

    with open(DOSSIER / "verite_terrain.csv", "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.DictWriter(f, fieldnames=list(lignes[0]))
        ecrivain.writeheader()
        ecrivain.writerows(lignes)
    print(f"{len(lignes)} images propres ecrites dans {dossier_images}")
    print(f"Lecture avec zxing: {lus}/{len(lignes)} ({100 * lus / len(lignes):.0f} %)")


if __name__ == "__main__":
    main()
