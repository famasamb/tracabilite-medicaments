"""Etape 35: entrainement de YOLOv8 (petit modele 'n') pour localiser le code DataMatrix.

Script autonome: il ne depend pas de l'application, donc il tourne aussi bien sur le PC que sur Google Colab.
Le resultat est le fichier modeles/datamatrix/weights/best.pt (meilleur modele sur le groupe de validation).

Exemples:
  python jeu_de_donnees/entrainer_yolo.py                                  (PC, processeur)
  python entrainer_yolo.py --donnees /content/yolo/data.yaml --appareil 0   (Colab, carte graphique)
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

DOSSIER = Path(__file__).resolve().parent
GRAINE = 35


def main() -> None:
    p = argparse.ArgumentParser(description="Entraine YOLOv8n sur le jeu d'images de codes DataMatrix")
    p.add_argument("--donnees", default=str(DOSSIER / "yolo" / "data.yaml"), help="chemin du data.yaml")
    p.add_argument("--epoques", type=int, default=50)
    p.add_argument("--taille", type=int, default=640, help="taille des images pendant l'entrainement")
    p.add_argument("--appareil", default="cpu", help="'cpu', ou '0' pour la premiere carte graphique")
    p.add_argument("--sortie", default=str(DOSSIER / "modeles"), help="dossier des resultats")
    a = p.parse_args()
    modele = YOLO("yolov8n.pt")  # poids pre-entraines sur COCO, telecharges au premier lancement
    modele.train(data=str(Path(a.donnees).resolve()), epochs=a.epoques, imgsz=a.taille, device=a.appareil,
                 seed=GRAINE, deterministic=True, project=str(Path(a.sortie).resolve()), name="datamatrix",
                 exist_ok=True, plots=True)
    print(f"Meilleur modele: {Path(a.sortie).resolve() / 'datamatrix' / 'weights' / 'best.pt'}")


if __name__ == "__main__":
    main()