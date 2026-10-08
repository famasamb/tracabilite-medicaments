"""Etape 55: evaluation des methodes de lecture sur de VRAIES photos de la planche imprimee (phase 3 et 4).

Rangement des photos (a faire a la main):
  jeu_de_donnees/photos_reelles/<condition>/<numero de serie>__<ce que vous voulez>.jpg
  ex.  photos_reelles/normal/59CCR54DAFX3__1.jpg      photos_reelles/lumiere_faible/42MPFZXYMHQV__2.jpg
Le dossier donne la condition de prise de vue; le texte avant "__" est le numero de serie ecrit sous le code,
c'est la verite terrain (une photo = un code). Le numero de serie peut aussi etre donne dans un fichier
photos_reelles/verite.csv (colonnes fichier,attendu) si vous preferez ne pas renommer.

Lancer depuis la racine du projet:  python -m jeu_de_donnees.evaluer_photos
Resultats: jeu_de_donnees/resultats/photos_reelles/ (lectures.csv, synthese.csv).
"""
import csv
import time
from collections import defaultdict
from pathlib import Path

from app.lecture import (CLASSIQUE, lire_code, lire_hybride, lire_zone,
                         localiseur_disponible)
from app.routes_evenements import extraire_numero_serie

DOSSIER = Path(__file__).parent
PHOTOS = DOSSIER / "photos_reelles"
SORTIE = DOSSIER / "resultats" / "photos_reelles"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TAILLE_MAX_APPLICATION = 5 * 1024 * 1024        # limite de l'application (obtenir_unite)
METHODES = ("classique", "deep_learning", "hybride")


def serie(texte: str | None) -> str | None:
    return extraire_numero_serie(texte) if texte else None


def lister_photos(dossier: Path) -> list[dict]:
    """Photos trouvees avec leur condition et leur numero de serie attendu (None si impossible a determiner)."""
    verite = {}
    if (dossier / "verite.csv").exists():
        with open(dossier / "verite.csv", newline="", encoding="utf-8-sig") as f:
            verite = {l["fichier"].replace("\\", "/"): l["attendu"].strip() for l in csv.DictReader(f)}
    lignes = []
    for chemin in sorted(dossier.rglob("*")):
        if chemin.suffix.lower() not in EXTENSIONS:
            continue
        relatif = chemin.relative_to(dossier).as_posix()
        condition = chemin.parent.name if chemin.parent != dossier else "autre"
        attendu = verite.get(relatif) or (chemin.stem.split("__")[0] if "__" in chemin.stem else None)
        lignes.append({"fichier": relatif, "condition": condition, "attendu": attendu, "chemin": chemin})
    return lignes


def lire_avec_les_trois(octets: bytes, localiseur) -> dict[str, tuple[str | None, float]]:
    """Fait lire la photo par chaque methode: (numero de serie lu, temps en ms)."""
    sortie = {}
    for nom in METHODES:
        debut = time.perf_counter()
        if nom == "classique":
            texte = lire_code(octets)
        elif nom == "deep_learning":
            texte = lire_zone(octets, localiseur) if localiseur else None
        else:
            texte = lire_hybride(octets, localiseur).texte if localiseur else lire_code(octets)
        sortie[nom] = (serie(texte), (time.perf_counter() - debut) * 1000)
    return sortie


def evaluer_dossier(dossier: Path, localiseur) -> list[dict]:
    photos = lister_photos(dossier)
    if photos and localiseur:   # un premier appel non compte (chargement des bibliotheques)
        lire_avec_les_trois(photos[0]["chemin"].read_bytes(), localiseur)
    resultats = []
    for p in photos:
        octets = p["chemin"].read_bytes()
        lectures = lire_avec_les_trois(octets, localiseur)
        ligne = {"fichier": p["fichier"], "condition": p["condition"], "attendu": p["attendu"] or "",
                 "tailleMo": round(len(octets) / 1048576, 2),
                 "tropLourdePourLApp": int(len(octets) > TAILLE_MAX_APPLICATION)}
        for nom, (lu, ms) in lectures.items():
            ligne[f"lu_{nom}"] = lu or ""
            ligne[f"ok_{nom}"] = int(bool(p["attendu"]) and lu == p["attendu"])
            ligne[f"ms_{nom}"] = round(ms, 1)
        resultats.append(ligne)
    return resultats


def synthetiser(resultats: list[dict]) -> list[dict]:
    """Une ligne par (condition, methode) puis une ligne 'toutes': rappel, precision, faux positifs, temps."""
    groupes = defaultdict(list)
    for r in resultats:
        groupes[r["condition"]].append(r)
        groupes["toutes"].append(r)
    lignes = []
    for condition in sorted(groupes, key=lambda c: (c == "toutes", c)):
        liste = groupes[condition]
        for nom in METHODES:
            lues = [r for r in liste if r[f"lu_{nom}"]]
            bonnes = [r for r in liste if r[f"ok_{nom}"]]
            lignes.append({
                "condition": condition, "methode": nom, "photos": len(liste), "lues": len(lues),
                "correctes": len(bonnes), "fausses": len(lues) - len(bonnes),
                "rappel": round(len(bonnes) / len(liste), 4),
                "precision": round(len(bonnes) / len(lues), 4) if lues else "",
                "tempsMoyenMs": round(sum(r[f"ms_{nom}"] for r in liste) / len(liste), 1)})
    return lignes


def ecrire(chemin: Path, lignes: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.DictWriter(f, fieldnames=list(lignes[0]))
        ecrivain.writeheader()
        ecrivain.writerows(lignes)


def main() -> None:
    if not PHOTOS.is_dir() or not lister_photos(PHOTOS):
        raise SystemExit(f"Aucune photo dans {PHOTOS}. Rangez-les dans photos_reelles/<condition>/<numero de serie>__1.jpg")
    photos = lister_photos(PHOTOS)
    sans_verite = [p["fichier"] for p in photos if not p["attendu"]]
    if sans_verite:
        raise SystemExit("Numero de serie attendu inconnu pour: " + ", ".join(sans_verite)
                         + "\nNommez-les <numero de serie>__n.jpg ou ajoutez-les dans photos_reelles/verite.csv.")
    localiseur = localiseur_disponible()
    if localiseur is None:
        print("Modele YOLO absent ou ultralytics manquant: seule la methode classique est evaluee.")
    resultats = evaluer_dossier(PHOTOS, localiseur)
    resume = synthetiser(resultats)
    ecrire(SORTIE / "lectures.csv", resultats)
    ecrire(SORTIE / "synthese.csv", resume)
    lourdes = [r["fichier"] for r in resultats if r["tropLourdePourLApp"]]
    print(f"{len(resultats)} photos evaluees.\n")
    print(f"  {'condition':<16}{'methode':<15}{'photos':>7}{'rappel':>9}{'precision':>11}{'fausses':>9}{'ms':>8}")
    for l in resume:
        precision = f"{100 * l['precision']:.0f} %" if l["precision"] != "" else "-"
        print(f"  {l['condition']:<16}{l['methode']:<15}{l['photos']:>7}{100 * l['rappel']:>8.0f} %"
              f"{precision:>11}{l['fausses']:>9}{l['tempsMoyenMs']:>8.0f}")
    echecs = [r["fichier"] for r in resultats if not r["ok_hybride"]]
    if echecs:
        print("\nPhotos non lues (ou mal lues) par l'hybride:", ", ".join(echecs))
    if lourdes:
        print(f"\nAttention: {len(lourdes)} photo(s) depassent 5 Mo, limite de l'application: {', '.join(lourdes)}")
    print(f"\nDetail: {SORTIE}")


if __name__ == "__main__":
    main()
