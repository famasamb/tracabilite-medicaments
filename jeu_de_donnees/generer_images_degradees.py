"""Etape 29: images degradees (flou et occlusion) a partir des images propres de l'etape 28.

Lancer depuis la racine du projet:  python -m jeu_de_donnees.generer_images_degradees
"""
import csv
import shutil
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from app.codes import lire_code

from .degradations import flouter, occulter

DOSSIER = Path(__file__).parent
FICHIER_CSV = DOSSIER / "verite_terrain.csv"
GRAINE = 2027
NIVEAUX_FLOU = {1: 3.0, 2: 5.0, 3: 6.0}          # ecart type du flou gaussien, en pixels
NIVEAUX_OCCLUSION = {1: 0.05, 2: 0.10, 3: 0.15}  # part de la surface du code cachee


def lire_image(chemin: Path) -> np.ndarray:
    image = cv2.imread(str(chemin))
    if image is None:
        raise FileNotFoundError(chemin)
    return image


def main() -> None:
    with open(FICHIER_CSV, newline="", encoding="utf-8") as f:
        propres = [l for l in csv.DictReader(f) if l["degradation"] == "aucune"]
    if not propres:
        raise SystemExit("Aucune image propre: lancez d'abord generer_images_propres.")
    dossier = DOSSIER / "images" / "degradees"
    shutil.rmtree(dossier, ignore_errors=True)
    dossier.mkdir(parents=True)
    generateur = np.random.default_rng(GRAINE)

    lignes = [{**l, "parametre": ""} for l in propres]
    lus: dict[tuple[str, int], int] = defaultdict(int)
    for ligne in propres:
        image = lire_image(DOSSIER / "images" / ligne["fichier"])
        position = tuple(int(ligne[k]) for k in ("x", "y", "largeur", "hauteur"))
        variantes = [("flou", n, p, flouter(image, p)) for n, p in NIVEAUX_FLOU.items()]
        variantes += [("occlusion", n, p, occulter(image, position, p, generateur))
                      for n, p in NIVEAUX_OCCLUSION.items()]
        for nom, niveau, parametre, resultat in variantes:
            fichier = f"{ligne['numeroSerie']}_{nom}{niveau}.png"
            cv2.imwrite(str(dossier / fichier), resultat)
            ok, relu = cv2.imencode(".png", resultat)
            lus[(nom, niveau)] += lire_code(relu.tobytes()) == ligne["contenuAttendu"]
            lignes.append({**ligne, "fichier": f"degradees/{fichier}", "degradation": nom,
                           "niveau": niveau, "parametre": parametre})

    with open(FICHIER_CSV, "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.DictWriter(f, fieldnames=list(lignes[0]))
        ecrivain.writeheader()
        ecrivain.writerows(lignes)
    print(f"{len(lignes) - len(propres)} images degradees ecrites dans {dossier}")
    print("Taux de lecture avec zxing (sur les images propres: 100 %):")
    for (nom, niveau), n in sorted(lus.items()):
        print(f"  {nom} niveau {niveau}: {n}/{len(propres)} ({100 * n / len(propres):.0f} %)")


if __name__ == "__main__":
    main()