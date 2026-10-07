"""Etape 37: evaluation du moteur d'anomalies (phase 5) contre les anomalies injectees.

Le moteur lit l'historique sans savoir ou sont les anomalies. On compare ce qu'il signale a la verite
terrain (anomalies_injectees.csv), type par type: precision, rappel. On verifie aussi qu'il ne
signale rien dans l'historique normal (historique.db), c'est-a-dire aucune fausse alerte.

Les quatre types sont traites. Les trois premiers sont des regles; la concentration inhabituelle est un
petit modele statistique par officine. Pour elle, on compte aussi les alertes par groupe (structure, lot):
une concentration est UNE alerte pour la personne qui verifie, meme si elle touche 150 evenements.

Lancer depuis la racine du projet:  python -m jeu_de_donnees.evaluer_anomalies
"""
import csv
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import TypeAnomalie
from app.moteur_anomalies import (DISTANCE_MIN_KM, VITESSE_MAX_KMH, Detection, analyser_base,
                                  charger_operations, etapes)

DOSSIER = Path(__file__).parent
TRAITES = [TypeAnomalie.reutilisationIdentifiant.value, TypeAnomalie.ruptureSequence.value,
           TypeAnomalie.trajetInhabituel.value, TypeAnomalie.concentrationInhabituelle.value]
CONCENTRATION = TypeAnomalie.concentrationInhabituelle


def comparer(detections: list[Detection], verite: set[tuple[str, str]], types: list[str]) -> list[dict]:
    """Une ligne par type: vrais positifs, fausses alertes, anomalies manquees, precision, rappel.

    detections et verite sont des ensembles de couples (type, identifiant d'evenement)."""
    trouvees = {(d.type.value, d.evenement_id) for d in detections}
    lignes = []
    for type_ in types:
        signalees = {c for c in trouvees if c[0] == type_}
        attendues = {c for c in verite if c[0] == type_}
        vrais = signalees & attendues
        lignes.append({
            "type": type_, "injectees": len(attendues), "signalees": len(signalees),
            "vraisPositifs": len(vrais), "faussesAlertes": len(signalees - attendues),
            "manquees": len(attendues - signalees),
            "precision": round(len(vrais) / len(signalees), 4) if signalees else "",
            "rappel": round(len(vrais) / len(attendues), 4) if attendues else ""})
    return lignes


def detecter(chemin_base: Path) -> list[Detection]:
    moteur = create_engine(f"sqlite:///{chemin_base.as_posix()}")
    with Session(moteur) as db:
        resultat = analyser_base(db)
    moteur.dispose()
    return resultat


def vitesses(chemin_base: Path) -> list[tuple[str, float, float]]:
    """(evenement, km, km/h) de chaque etape entre deux evenements localises d'une meme unite."""
    moteur = create_engine(f"sqlite:///{chemin_base.as_posix()}")
    resultat = []
    with Session(moteur) as db:
        for operations in charger_operations(db).values():
            ordonnees = sorted(operations, key=lambda o: (o.dateHeure, o.id))
            resultat += [(o.id, km, km / heures if heures > 0 else float("inf")) for o, km, heures in etapes(ordonnees)]
    moteur.dispose()
    return resultat


def groupes(detections: list[Detection]) -> set[str]:
    """Les alertes de concentration, une par couple (structure, lot)."""
    return {d.groupe for d in detections if d.type == CONCENTRATION and d.groupe}


def groupes_injectes(chemin_base: Path, evenements: set[str]) -> set[str]:
    """Les couples (structure, lot) auxquels appartiennent les evenements de concentration injectes."""
    moteur = create_engine(f"sqlite:///{chemin_base.as_posix()}")
    resultat = set()
    with Session(moteur) as db:
        for operations in charger_operations(db).values():
            resultat |= {f"{o.structure_id}/{o.lot_id}" for o in operations if o.id in evenements}
    moteur.dispose()
    return resultat


def pourcentage(valeur) -> str:
    return f"{100 * valeur:.1f} %" if valeur != "" else "-"


def main() -> None:
    for nom in ("historique.db", "historique_anomalies.db"):
        if not (DOSSIER / nom).exists():
            raise SystemExit(f"{nom} absent: lancez d'abord generer_historique puis injecter_anomalies.")

    normal = detecter(DOSSIER / "historique.db")
    regles = [d for d in normal if d.type != CONCENTRATION]
    print(f"Historique normal (historique.db): {len(regles)} anomalie(s) signalee(s) par les regles, attendu 0.")
    fausses_groupes = groupes(normal)
    print(f"  concentration: {len(fausses_groupes)} alerte(s) (structure/lot) dans l'historique normal"
          + (f": {', '.join(sorted(fausses_groupes))}" if fausses_groupes else "") + ".")

    with open(DOSSIER / "anomalies_injectees.csv", newline="", encoding="utf-8") as f:
        injectees = list(csv.DictReader(f))
    verite = {(l["typeAnomalie"], l["evenement_id"]) for l in injectees}
    detections = detecter(DOSSIER / "historique_anomalies.db")
    lignes = comparer(detections, verite, TRAITES)

    print("\nHistorique avec anomalies (historique_anomalies.db):")
    print(f"  {'type':<28}{'injectees':>10}{'signalees':>10}{'justes':>8}{'fausses':>9}{'manquees':>9}{'precision':>11}{'rappel':>9}")
    for l in lignes:
        print(f"  {l['type']:<28}{l['injectees']:>10}{l['signalees']:>10}{l['vraisPositifs']:>8}"
              f"{l['faussesAlertes']:>9}{l['manquees']:>9}{pourcentage(l['precision']):>11}{pourcentage(l['rappel']):>9}")
    evenements_conc = {c[1] for c in verite if c[0] == CONCENTRATION.value}
    vraies = groupes_injectes(DOSSIER / "historique_anomalies.db", evenements_conc)
    trouvees = groupes(detections)
    print(f"\nConcentration, par alerte (structure/lot): {len(vraies)} injectee(s), {len(trouvees)} signalee(s), "
          f"{len(vraies & trouvees)} juste(s), {len(trouvees - vraies)} fausse(s).")
    for g in sorted(trouvees - vraies):
        d = next(d for d in detections if d.groupe == g)
        print(f"  fausse alerte {g}: {d.description}")

    # Ce que les donnees disent du seuil de vitesse (le seuil lui-meme est un choix: voir moteur_anomalies)
    trajets = {c[1] for c in verite if c[0] == TypeAnomalie.trajetInhabituel.value}
    etapes_normales = [v for e, km, v in vitesses(DOSSIER / "historique.db")]
    etapes_injectees = [v for e, km, v in vitesses(DOSSIER / "historique_anomalies.db") if e in trajets]
    print(f"\nVitesses entre deux evenements localises d'une meme unite:")
    print(f"  historique normal: maximum {max(etapes_normales):.1f} km/h sur {len(etapes_normales)} etapes")
    print(f"  trajets injectes:  minimum {min(etapes_injectees):.1f} km/h sur {len(etapes_injectees)} etapes")
    print(f"  seuil du moteur:   {VITESSE_MAX_KMH:.0f} km/h, pour des distances d'au moins {DISTANCE_MIN_KM:.0f} km")

    sortie = DOSSIER / "resultats" / "anomalies"
    sortie.mkdir(parents=True, exist_ok=True)
    with open(sortie / "synthese_regles.csv", "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.DictWriter(f, fieldnames=list(lignes[0]))
        ecrivain.writeheader()
        ecrivain.writerows(lignes)
    print(f"\nResultats ecrits dans {sortie}")


if __name__ == "__main__":
    main()