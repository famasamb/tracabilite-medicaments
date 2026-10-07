"""Preparation du jeu d'images au format YOLO (phase 4, entrainement du modele de localisation).

Regles:
  - une seule classe: le code DataMatrix (classe 0);
  - une etiquette par image: "0 xcentre ycentre largeur hauteur", valeurs entre 0 et 1;
  - la repartition apprentissage / validation / test se fait par CODE DE BASE (numero de serie):
    les 7 versions d'un meme code (propre, 3 floues, 3 occultees) restent toutes dans le meme groupe,
    sinon le modele serait evalue sur des images qu'il a deja vues sous une autre forme.
"""
import random
import shutil
from pathlib import Path

PROPORTIONS = (("train", 0.70), ("val", 0.15), ("test", 0.15))


def repartir(numeros_serie: list[str], graine: int) -> dict[str, str]:
    """Associe chaque numero de serie a 'train', 'val' ou 'test' (tirage reproductible)."""
    numeros = sorted(set(numeros_serie))
    random.Random(graine).shuffle(numeros)
    total = len(numeros)
    n_val = round(total * PROPORTIONS[1][1])
    n_test = round(total * PROPORTIONS[2][1])
    groupes = {}
    for i, numero in enumerate(numeros):
        if i < n_test:
            groupes[numero] = "test"
        elif i < n_test + n_val:
            groupes[numero] = "val"
        else:
            groupes[numero] = "train"
    return groupes


def ligne_yolo(ligne: dict) -> str:
    """Etiquette YOLO d'une ligne de verite_terrain.csv (x, y = coin haut gauche, en pixels)."""
    W, H = int(ligne["largeurImage"]), int(ligne["hauteurImage"])
    x, y, l, h = (int(ligne[c]) for c in ("x", "y", "largeur", "hauteur"))
    return f"0 {(x + l / 2) / W:.6f} {(y + h / 2) / H:.6f} {l / W:.6f} {h / H:.6f}"


def preparer(lignes: list[dict], dossier_images: Path, sortie: Path, graine: int) -> dict[str, str]:
    """Copie les images et ecrit les etiquettes dans sortie/images/<groupe> et sortie/labels/<groupe>."""
    groupes = repartir([l["numeroSerie"] for l in lignes], graine)
    for groupe, _ in PROPORTIONS:
        (sortie / "images" / groupe).mkdir(parents=True, exist_ok=True)
        (sortie / "labels" / groupe).mkdir(parents=True, exist_ok=True)
    for ligne in lignes:
        groupe = groupes[ligne["numeroSerie"]]
        source = dossier_images / ligne["fichier"]
        shutil.copyfile(source, sortie / "images" / groupe / source.name)
        (sortie / "labels" / groupe / f"{source.stem}.txt").write_text(ligne_yolo(ligne) + "\n", encoding="utf-8")
    (sortie / "data.yaml").write_text(
        "train: images/train\nval: images/val\ntest: images/test\nnames:\n  0: datamatrix\n", encoding="utf-8")
    return groupes