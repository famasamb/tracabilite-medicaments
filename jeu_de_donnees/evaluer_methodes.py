"""Etape 33: evaluation des methodes de lecture sur le jeu de donnees (phase 4).

Pour l'instant, seule la methode classique existe. Les methodes deep learning et hybride
s'ajouteront au dictionnaire METHODES aux etapes suivantes.

Lancer depuis la racine du projet:  python -m jeu_de_donnees.evaluer_methodes
"""
import csv
from pathlib import Path

from .evaluation import Resultat, evaluer, methode_classique, synthese

DOSSIER = Path(__file__).parent
SORTIE = DOSSIER / "resultats"
METHODES = {"classique": methode_classique}


def ecrire(chemin: Path, lignes: list[dict]) -> None:
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.DictWriter(f, fieldnames=list(lignes[0]))
        ecrivain.writeheader()
        ecrivain.writerows(lignes)


def main() -> None:
    with open(DOSSIER / "verite_terrain.csv", newline="", encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    SORTIE.mkdir(exist_ok=True)
    for nom, methode in METHODES.items():
        resultats: list[Resultat] = evaluer(methode, lignes, DOSSIER / "images")
        ecrire(SORTIE / f"lectures_{nom}.csv", [
            {"fichier": r.fichier, "degradation": r.degradation, "niveau": r.niveau,
             "attendu": r.attendu, "lu": r.lu or "", "correct": int(r.correct),
             "tempsMs": round(r.temps_ms, 2)} for r in resultats])
        resume = synthese(resultats)
        ecrire(SORTIE / f"synthese_{nom}.csv", resume)
        print(f"Methode {nom}: {len(resultats)} images")
        print(f"  {'degradation':<12}{'niveau':>7}{'images':>8}{'rappel':>9}{'precision':>11}{'temps (ms)':>12}")
        for l in resume:
            precision = f"{100 * l['precision']:.1f} %" if l["precision"] != "" else "-"
            print(f"  {l['degradation']:<12}{l['niveau']:>7}{l['images']:>8}"
                  f"{100 * l['rappel']:>8.1f} %{precision:>11}{l['tempsMoyenMs']:>12.2f}")


if __name__ == "__main__":
    main()