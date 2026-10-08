"""Moteur d'anomalies (phase 5 de la methodologie): reutilisation, rupture, trajet inhabituel, concentration.

Les deux premieres regles sont celles que l'application applique deja au moment de l'enregistrement
(fiche 7, variante 3b; fiche 8, variantes 3b et 3c). Le moteur les applique ici a un historique complet,
evenement par evenement, dans l'ordre du temps:

  reutilisationIdentifiant : l'unite avait deja ete dispensee (son identifiant est desactive).
  ruptureSequence          : une officine dispense une unite qu'elle n'a jamais recue, ou une structure recoit
                             une unite qu'aucune autre structure n'a jamais expediee.
  trajetInhabituel         : l'unite se retrouve, en peu de temps, trop loin de son evenement precedent:
                             la vitesse moyenne entre les deux depasse ce qu'un vehicule peut faire.
  concentrationInhabituelle: une officine recoit, dans un seul lot, beaucoup plus d'unites que ce qu'elle
                             recoit d'habitude d'un lot (modele statistique propre a chaque officine).

Comme dans la fiche 8, une reutilisation arrete l'analyse de la regle de rupture pour cet evenement.
Un meme evenement peut en revanche reveler un trajet inhabituel en plus. Une detection est un signal
a verifier par une personne, pas une fraude confirmee.

Les detections sont ecrites dans la table des anomalies (statut "a_verifier") par `lancer_analyse`, ce
qui alimente le tableau de bord. L'ecriture est sans doublon: une anomalie deja presente pour le meme
evenement et le meme type (par exemple enregistree par l'API au moment de l'evenement) n'est pas recreee.
Lancer depuis la racine du projet:  python -m app.moteur_anomalies
"""
from dataclasses import dataclass
from datetime import datetime
from statistics import median

from sqlalchemy.orm import Session

from .geo import distance_km
from .models import Anomalie, Evenement, Lot, Structure, TypeAnomalie, TypeOperation, TypeStructure, Unite, Utilisateur

SCORE_REGLE = 1.0   # une regle est vraie ou fausse: meme score que dans les routes

# Parametres du trajet inhabituel. Ce sont des choix, a valider avec le maitre de stage.
VITESSE_MAX_KMH = 120.0   # vitesse moyenne a vol d'oiseau au-dela de laquelle un trajet routier est invraisemblable
DISTANCE_MIN_KM = 50.0    # en dessous, l'imprecision du GPS rend la vitesse sans signification

# Parametres de la concentration inhabituelle. Ce sont aussi des choix, a valider avec le maitre de stage.
Z_MAX = 3.5               # seuil du z-score modifie (convention de Iglewicz et Hoaglin pour reperer une valeur aberrante)
LOTS_MIN = 5              # nombre minimal d'autres lots pour juger une officine; sinon elle n'a pas d'habitude connue
MAD_MIN = 1.0             # plancher de la dispersion: evite de diviser par zero si les lots sont tous identiques
COEFF_Z = 0.6745          # rend la deviation absolue mediane comparable a un ecart type


@dataclass(frozen=True)
class Operation:
    """Ce que le moteur voit d'un evenement."""
    id: str
    numeroSerie: str
    type: TypeOperation
    dateHeure: datetime
    structure_id: str
    latitude: float | None
    longitude: float | None
    lot_id: str | None = None                   # lot de l'unite (necessaire a la concentration)
    structure_type: TypeStructure | None = None  # type de la structure qui a enregistre l'evenement
    numeroLot: str | None = None                # numero de lot imprime, pour les descriptions


@dataclass(frozen=True)
class Detection:
    evenement_id: str
    numeroSerie: str
    type: TypeAnomalie
    score: float
    description: str
    groupe: str | None = None   # concentration: "structure/lot", pour regrouper les evenements d'une meme alerte


def est_reutilisation(avant: list[Operation]) -> bool:
    """Vrai si l'unite a deja ete dispensee avant l'evenement courant."""
    return any(a.type == TypeOperation.dispensation for a in avant)


def est_rupture(avant: list[Operation], courant: Operation) -> bool:
    """Vrai si l'evenement rompt la sequence: dispensation sans reception par cette structure, ou reception
    d'une unite qu'aucune autre structure n'a expediee."""
    if courant.type == TypeOperation.dispensation:
        return not any(a.type == TypeOperation.reception and a.structure_id == courant.structure_id for a in avant)
    if courant.type == TypeOperation.reception:
        return not any(a.type == TypeOperation.expedition and a.structure_id != courant.structure_id for a in avant)
    return False


def a_une_position(o: Operation) -> bool:
    return o.latitude is not None and o.longitude is not None


def etapes(ordonnees: list[Operation]) -> list[tuple[Operation, float, float]]:
    """Pour chaque evenement localise, distance (km) et duree (heures) depuis l'evenement localise precedent.

    Les evenements sans position GPS sont ignores: on relie deux positions connues."""
    resultat = []
    precedent = None
    for o in ordonnees:
        if not a_une_position(o):
            continue
        if precedent is not None:
            km = distance_km((precedent.latitude, precedent.longitude), (o.latitude, o.longitude))
            heures = (o.dateHeure - precedent.dateHeure).total_seconds() / 3600
            resultat.append((o, km, heures))
        precedent = o
    return resultat


def est_trajet_inhabituel(km: float, heures: float) -> bool:
    """Vrai si la distance est assez grande pour compter et la vitesse moyenne depasse le maximum."""
    if km < DISTANCE_MIN_KM:
        return False
    return heures <= 0 or km / heures > VITESSE_MAX_KMH


def analyser_unite(operations: list[Operation]) -> list[Detection]:
    """Analyse l'historique d'une seule unite, classe du plus ancien au plus recent."""
    ordonnees = sorted(operations, key=lambda o: (o.dateHeure, o.id))
    depuis_precedent = {o.id: (km, heures) for o, km, heures in etapes(ordonnees)}
    detections = []
    for i, courant in enumerate(ordonnees):
        avant = ordonnees[:i]
        if est_reutilisation(avant):
            detections.append(Detection(
                courant.id, courant.numeroSerie, TypeAnomalie.reutilisationIdentifiant, SCORE_REGLE,
                "unite deja dispensee, identifiant desactive"))
        elif est_rupture(avant, courant):
            detections.append(Detection(
                courant.id, courant.numeroSerie, TypeAnomalie.ruptureSequence, SCORE_REGLE,
                ("dispensation sans reception par cette structure dans l'historique"
                 if courant.type == TypeOperation.dispensation
                 else "reception sans expedition par une autre structure dans l'historique")))
        if courant.id in depuis_precedent and est_trajet_inhabituel(*depuis_precedent[courant.id]):
            km, heures = depuis_precedent[courant.id]
            duree = f"{heures * 60:.0f} min" if heures < 2 else f"{heures:.1f} h"
            detections.append(Detection(
                courant.id, courant.numeroSerie, TypeAnomalie.trajetInhabituel, SCORE_REGLE,
                f"{km:.0f} km parcourus en {duree} depuis l'evenement precedent"))
    return detections


def score_concentration(z: float) -> float:
    """Entre 0,5 (au seuil) et 1 (tres loin du seuil)."""
    return z / (z + Z_MAX)


def detecter_concentrations(operations: list[Operation]) -> list[Detection]:
    """Reperer les (officine, lot) dont la quantite recue sort de l'habitude de cette officine.

    Pour chaque officine, la quantite d'un lot est le nombre d'unites distinctes qu'elle en a recues.
    Elle est comparee a la mediane et a la deviation absolue mediane (MAD) des AUTRES lots de la meme
    officine: z = 0,6745 * (quantite - mediane) / MAD. Seul un exces (z > Z_MAX) est signale.
    Une officine qui n'a pas au moins LOTS_MIN autres lots n'est pas jugee. Tous les evenements de
    reception du couple signale sont rapportes, avec le meme groupe."""
    receptions = [o for o in operations
                  if o.type == TypeOperation.reception and o.structure_type == TypeStructure.officine
                  and o.lot_id is not None]
    unites: dict[tuple[str, str], set[str]] = {}
    evenements: dict[tuple[str, str], list[Operation]] = {}
    for o in receptions:
        cle = (o.structure_id, o.lot_id)
        unites.setdefault(cle, set()).add(o.numeroSerie)
        evenements.setdefault(cle, []).append(o)

    detections = []
    for (structure, lot), recues in sorted(unites.items()):
        autres = [len(u) for (s, l), u in unites.items() if s == structure and l != lot]
        if len(autres) < LOTS_MIN:
            continue
        centre = median(autres)
        mad = max(median(abs(x - centre) for x in autres), MAD_MIN)
        z = COEFF_Z * (len(recues) - centre) / mad
        if z <= Z_MAX:
            continue
        numero = evenements[(structure, lot)][0].numeroLot or lot
        description = (f"{len(recues)} unites du lot {numero} recues par cette structure, contre {centre:g} "
                       f"unites en general par lot (z = {z:.1f})")
        for o in sorted(evenements[(structure, lot)], key=lambda o: (o.dateHeure, o.id)):
            detections.append(Detection(o.id, o.numeroSerie, TypeAnomalie.concentrationInhabituelle,
                                        round(score_concentration(z), 4), description, f"{structure}/{lot}"))
    return detections


def charger_operations(db: Session) -> dict[str, list[Operation]]:
    """Tous les evenements de la base, regroupes par unite."""
    lignes = (db.query(Evenement, Utilisateur.structure_id, Structure.type, Unite.lot_id, Lot.numeroLot)
              .join(Utilisateur, Evenement.utilisateur_id == Utilisateur.id)
              .join(Structure, Utilisateur.structure_id == Structure.id)
              .outerjoin(Unite, Evenement.numeroSerie == Unite.numeroSerie)
              .outerjoin(Lot, Unite.lot_id == Lot.id).all())
    par_unite: dict[str, list[Operation]] = {}
    for e, structure_id, structure_type, lot_id, numero_lot in lignes:
        par_unite.setdefault(e.numeroSerie, []).append(Operation(
            e.id, e.numeroSerie, e.typeOperation, e.dateHeure, structure_id, e.latitude, e.longitude,
            lot_id, structure_type, numero_lot))
    return par_unite


def analyser_base(db: Session) -> list[Detection]:
    """Applique les regles et le modele statistique a tout l'historique (lecture seule: rien n'est ecrit)."""
    par_unite = charger_operations(db)
    detections: list[Detection] = []
    for operations in par_unite.values():
        detections += analyser_unite(operations)
    detections += detecter_concentrations([o for ops in par_unite.values() for o in ops])
    return detections


def enregistrer(db: Session, detections: list[Detection]) -> int:
    """Ajoute une ligne Anomalie par detection nouvelle (meme evenement et meme type = deja connue).

    Ne valide pas la transaction. Renvoie le nombre de lignes ajoutees."""
    connues = {(e, t) for e, t in db.query(Anomalie.evenement_id, Anomalie.typeAnomalie).all()}
    ajoutees = 0
    for d in detections:
        if (d.evenement_id, d.type) in connues:
            continue
        db.add(Anomalie(typeAnomalie=d.type, score=d.score, evenement_id=d.evenement_id))
        connues.add((d.evenement_id, d.type))
        ajoutees += 1
    return ajoutees


def lancer_analyse(db: Session) -> tuple[int, int]:
    """Analyse tout l'historique, ecrit les anomalies nouvelles et valide. Renvoie (detections, ajoutees)."""
    detections = analyser_base(db)
    ajoutees = enregistrer(db, detections)
    db.commit()
    return len(detections), ajoutees


def main() -> None:
    from .db import SessionLocal
    with SessionLocal() as db:
        detections, ajoutees = lancer_analyse(db)
    print(f"{detections} detection(s), dont {ajoutees} nouvelle(s) ecrite(s) dans la table des anomalies.")


if __name__ == "__main__":
    main()
