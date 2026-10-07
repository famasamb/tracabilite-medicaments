"""Etape 34: prepare le jeu d'images au format YOLO.

Ecrit jeu_de_donnees/yolo/ (images, etiquettes, data.yaml) et jeu_de_donnees/repartition.csv.
Lancer depuis la racine du projet:  python -m jeu_de_donnees.preparer_yolo
"""
import csv
import shutil
from collections import Counter
from pathlib import Path

from .yolo import preparer

DOSSIER = Path(__file__).parent
SORTIE = DOSSIER / "yolo"
GRAINE = 34


def main() -> None:
    with open(DOSSIER / "verite_terrain.csv", newline="", encoding="utf-8") as f:
        lignes = [l for l in csv.DictReader(f) if l["source"] == "synthetique"]
    if SORTIE.exists():
        shutil.rmtree(SORTIE)
    groupes = preparer(lignes, DOSSIER / "images", SORTIE, GRAINE)
    with open(DOSSIER / "repartition.csv", "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.writer(f)
        ecrivain.writerow(["fichier", "numeroSerie", "groupe"])
        for l in lignes:
            ecrivain.writerow([l["fichier"], l["numeroSerie"], groupes[l["numeroSerie"]]])
    codes = Counter(groupes.values())
    images = Counter(groupes[l["numeroSerie"]] for l in lignes)
    print(f"{len(lignes)} images, {len(groupes)} codes de base, graine {GRAINE}")
    for g in ("train", "val", "test"):
        print(f"  {g:<6}{codes[g]:>4} codes{images[g]:>6} images")
    print(f"Dossier YOLO: {SORTIE}")


if __name__ == "__main__":
    main()