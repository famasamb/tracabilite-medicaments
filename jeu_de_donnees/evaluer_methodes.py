"""Etapes 33 et 36: evaluation des methodes de lecture sur le jeu de donnees (phase 4).

Methodes: classique, deep learning (YOLO localise, zxing lit), hybride (classique puis deep learning).
Par defaut, l'evaluation porte sur le groupe TEST (15 codes de base, 105 images, jamais utilises pour
entrainer ni pour choisir le modele): c'est la comparaison equitable. Avec --groupe toutes, les 700 images.

Lancer depuis la racine du projet:
  python -m jeu_de_donnees.evaluer_methodes
  python -m jeu_de_donnees.evaluer_methodes --groupe toutes
"""
import argparse
import csv
from pathlib import Path

from .evaluation import Methode, Resultat, evaluer, methode_classique, synthese
from .methodes_dl import MODELE, localiseur_yolo, methode_deep_learning, methode_hybride

DOSSIER = Path(__file__).parent
SORTIE = DOSSIER / "resultats"


def ecrire(chemin: Path, lignes: list[dict]) -> None:
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.DictWriter(f, fieldnames=list(lignes[0]))
        ecrivain.writeheader()
        ecrivain.writerows(lignes)


def lignes_du_groupe(groupe: str) -> list[dict]:
    with open(DOSSIER / "verite_terrain.csv", newline="", encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    if groupe == "toutes":
        return lignes
    with open(DOSSIER / "repartition.csv", newline="", encoding="utf-8") as f:
        du_groupe = {l["fichier"] for l in csv.DictReader(f) if l["groupe"] == groupe}
    return [l for l in lignes if l["fichier"] in du_groupe]


def methodes_disponibles() -> dict[str, Methode]:
    methodes: dict[str, Methode] = {"classique": methode_classique}
    if MODELE.exists():
        dl = methode_deep_learning(localiseur_yolo())
        methodes["deep_learning"] = dl
        methodes["hybride"] = methode_hybride(methode_classique, dl)
    else:
        print(f"Modele YOLO absent ({MODELE}): seule la methode classique est evaluee.")
    return methodes


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--groupe", choices=["train", "val", "test", "toutes"], default="test")
    groupe = p.parse_args().groupe
    lignes = lignes_du_groupe(groupe)
    dossier_sortie = SORTIE / groupe
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    comparaison = []
    for nom, methode in methodes_disponibles().items():
        resultats: list[Resultat] = evaluer(methode, lignes, DOSSIER / "images")
        ecrire(dossier_sortie / f"lectures_{nom}.csv", [
            {"fichier": r.fichier, "degradation": r.degradation, "niveau": r.niveau,
             "attendu": r.attendu, "lu": r.lu or "", "correct": int(r.correct),
             "tempsMs": round(r.temps_ms, 2)} for r in resultats])
        resume = synthese(resultats)
        ecrire(dossier_sortie / f"synthese_{nom}.csv", resume)
        comparaison += [{"methode": nom, **l} for l in resume]
        print(f"\nMethode {nom}: {len(resultats)} images (groupe {groupe})")
        print(f"  {'degradation':<12}{'niveau':>7}{'images':>8}{'rappel':>9}{'precision':>11}{'temps (ms)':>12}")
        for l in resume:
            precision = f"{100 * l['precision']:.1f} %" if l["precision"] != "" else "-"
            print(f"  {l['degradation']:<12}{l['niveau']:>7}{l['images']:>8}"
                  f"{100 * l['rappel']:>8.1f} %{precision:>11}{l['tempsMoyenMs']:>12.2f}")
    ecrire(dossier_sortie / "comparaison.csv", comparaison)
    print("\nResume (toutes les images du groupe):")
    print(f"  {'methode':<15}{'rappel':>9}{'precision':>11}{'temps (ms)':>12}")
    for l in comparaison:
        if l["degradation"] == "toutes":
            precision = f"{100 * l['precision']:.1f} %" if l["precision"] != "" else "-"
            print(f"  {l['methode']:<15}{100 * l['rappel']:>8.1f} %{precision:>11}{l['tempsMoyenMs']:>12.2f}")


if __name__ == "__main__":
    main()