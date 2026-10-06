"""Base de reference des autorisations officielles (voir la fiche S'inscrire)."""
import csv
from pathlib import Path

from sqlalchemy.orm import Session

from .models import ReferenceAutorisation, TypeStructure


def charger_references(db: Session, chemin_csv: str | Path) -> int:
    """Importe un fichier CSV (colonnes: reference, nom, type). Renvoie le nombre de lignes ajoutees.

    Une reference deja presente n'est pas dupliquee.
    """
    ajoutees = 0
    with open(chemin_csv, newline="", encoding="utf-8") as fichier:
        for ligne in csv.DictReader(fichier):
            reference = ligne["reference"].strip()
            if not reference or db.get(ReferenceAutorisation, reference):
                continue
            db.add(ReferenceAutorisation(reference=reference, nom=ligne["nom"].strip(),
                                         type=TypeStructure(ligne["type"].strip())))
            ajoutees += 1
    db.commit()
    return ajoutees


def trouver_reference(db: Session, reference: str, type_: TypeStructure) -> ReferenceAutorisation | None:
    """Renvoie la reference si elle existe ET correspond au type de structure indique."""
    trouvee = db.get(ReferenceAutorisation, reference.strip())
    return trouvee if trouvee and trouvee.type == type_ else None