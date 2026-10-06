"""Les Services Regionaux d'Approvisionnement (SR), subdivisions internes de la PNA."""
import csv
from pathlib import Path

from .models import Structure, TypeStructure

# Liste de travail: a verifier avec le maitre de stage (voir le fichier CSV)
CHEMIN_SR = Path(__file__).resolve().parent.parent / "data" / "sr_a_verifier.csv"


def creer_sr(pna: Structure, chemin_csv: str | Path = CHEMIN_SR) -> list[Structure]:
    """Fabrique les SR d'une PNA, rattaches a elle (association "rattacher a"). Un SR ne s'inscrit pas."""
    with open(chemin_csv, newline="", encoding="utf-8") as fichier:
        return [Structure(nom=ligne["nom"].strip(), type=TypeStructure.SR,
                          localisation=ligne["localisation"].strip(), mere=pna)
                for ligne in csv.DictReader(fichier)]