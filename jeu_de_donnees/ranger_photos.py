"""Range les photos prises avec le telephone (une condition a la fois) pour l'evaluation (etape 55).

Principe: on photographie les 12 codes de la planche DANS L'ORDRE de la planche (de gauche a droite, ligne par
ligne, comme dans planche_codes.csv), en gardant la meme condition de prise de vue pour toute la serie.
Ce script copie ensuite les photos, triees par nom (le telephone nomme ses photos dans l'ordre de prise),
vers  photos_reelles/<condition>/<numero de serie>__<n>.jpg  : le numero de serie est la verite terrain.

Lancer depuis la racine du projet:
    python -m jeu_de_donnees.ranger_photos <dossier des photos> <condition>
    ex.  python -m jeu_de_donnees.ranger_photos C:\\Users\\SAGAR\\Desktop\\serie_normal normal
- 12 photos par serie, ou un multiple de 12 (plusieurs passages: les photos 13 a 24 sont la 2e photo de chaque code...).
- les photos originales ne sont jamais modifiees ni deplacees.
"""
import csv
import shutil
import sys
from pathlib import Path

DOSSIER = Path(__file__).parent
PHOTOS = DOSSIER / "photos_reelles"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def ordre_de_la_planche() -> list[str]:
    chemin = DOSSIER / "planche_codes.csv"
    if not chemin.exists():
        raise SystemExit("planche_codes.csv est absent: lance d'abord  python -m jeu_de_donnees.generer_planche")
    with open(chemin, newline="", encoding="utf-8") as f:
        return [l["numeroSerie"] for l in sorted(csv.DictReader(f), key=lambda l: int(l["ordre"]))]


def associer(photos: list[Path], series: list[str]) -> list[tuple[Path, str, int]]:
    """(photo, numero de serie, numero du passage) en suivant l'ordre de la planche, passage apres passage."""
    if not photos or len(photos) % len(series):
        raise ValueError(f"{len(photos)} photos: il en faut {len(series)} par passage (ou un multiple).")
    return [(p, series[i % len(series)], i // len(series) + 1) for i, p in enumerate(photos)]


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit(__doc__)
    source, condition = Path(argv[0]), argv[1].strip()
    if not source.is_dir():
        raise SystemExit(f"Dossier introuvable: {source}")
    if not condition or any(c in condition for c in '\\/:*?"<>|'):
        raise SystemExit("La condition doit etre un mot simple (normal, penche, lumiere_faible, loin, reflet, bouge...).")
    series = ordre_de_la_planche()
    photos = sorted((p for p in source.iterdir() if p.suffix.lower() in EXTENSIONS), key=lambda p: p.name.lower())
    try:
        plan = associer(photos, series)
    except ValueError as erreur:
        raise SystemExit(f"{erreur}\nLes photos ratees doivent etre refaites: la serie doit rester complete et dans l'ordre.")
    sortie = PHOTOS / condition
    sortie.mkdir(parents=True, exist_ok=True)
    print(f"Condition '{condition}': {len(plan)} photos")
    from app.codes import lire_code   # import tardif: garde ce module leger pour les tests
    from app.routes_evenements import extraire_numero_serie
    decalees = 0
    for photo, serie, passage in plan:
        cible = sortie / f"{serie}__{passage}{photo.suffix.lower()}"
        shutil.copyfile(photo, cible)
        lu = None
        try:
            texte = lire_code(photo.read_bytes())
            lu = extraire_numero_serie(texte) if texte else None
        except Exception:  # noqa: BLE001 - la verification est facultative
            pass
        alerte = ""
        if lu and lu != serie and lu in series:   # lu = un autre code de la planche: l'ordre n'a pas ete respecte
            alerte = f"   <-- ATTENTION: la lecture trouve {lu}"
            decalees += 1
        print(f"  {photo.name:<32} -> {cible.relative_to(DOSSIER)}{alerte}")
    if decalees:
        print(f"\n{decalees} photo(s) semblent ne pas suivre l'ordre de la planche. Verifie l'ordre, supprime "
              f"photos_reelles/{condition} et recommence (une photo manquante decale toutes les suivantes).")
    else:
        print("\nRangement termine. Evaluation:  python -m jeu_de_donnees.evaluer_photos")


if __name__ == "__main__":
    main(sys.argv[1:])
