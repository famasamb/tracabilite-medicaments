"""Etape 32: injection des anomalies dans l'historique (phase 3 de la methodologie).

On part de l'historique normal (historique.db, etape 31) et on le copie dans
historique_anomalies.db, qui recoit 12 reutilisations d'identifiant, 12 ruptures de sequence,
12 trajets inhabituels et une concentration inhabituelle (un lot de 150 unites livre a une seule
officine). La verite terrain est ecrite dans anomalies_injectees.csv.

Lancer depuis la racine du projet:  python -m jeu_de_donnees.injecter_anomalies
"""
import csv
import io
import os
import shutil
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

DOSSIER = Path(__file__).parent
SOURCE = DOSSIER / "historique.db"
COPIE = DOSSIER / "historique_anomalies.db"
if not SOURCE.exists():
    raise SystemExit("Historique normal absent: lancez d'abord generer_historique.")
shutil.copyfile(SOURCE, COPIE)
os.environ["DATABASE_URL"] = f"sqlite:///{COPIE.as_posix()}"

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (Evenement, StatutUnite, Structure, TypeOperation, Unite,  # noqa: E402
                        Utilisateur, new_id)

from .anomalies import injecter_reutilisations, injecter_ruptures, injecter_trajets  # noqa: E402
from .simulation import Acteur, EvenementSimule, simuler_historique  # noqa: E402

GRAINE = 32
MOT_DE_PASSE = "MotDePasseHistorique1"      # celui de generer_historique
FIN = datetime(2026, 10, 5, 23, 59)         # fin de la periode simulee, comme dans generer_historique
PAR_TYPE = 12
LOT_CONCENTRATION, UNITES_CONCENTRATION = "HS-CONC", 150
DEBUT_CONCENTRATION = datetime(2026, 9, 14, 8, 0)
VILLE_CONCENTRATION = "Louga"
PRODUIT_CONCENTRATION = "Paracetamol 500 mg"


def entete(client, login) -> dict:
    r = client.post("/auth/connexion", data={"username": login, "password": MOT_DE_PASSE})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def identifiant_produit(client, entete_labo, nom) -> str:
    """Identifiant du produit enregistre sous ce nom (recherche par l'API)."""
    return next(p["id"] for p in client.get("/produits", headers=entete_labo, params={"q": nom}).json())


def main() -> None:
    g = np.random.default_rng(GRAINE)

    # Le laboratoire serialise le lot de la concentration par la vraie route
    with TestClient(app) as client:
        labo = entete(client, "labo.hist")
        r = client.post("/lots/serialisation", headers=labo, json={
            "produit_id": identifiant_produit(client, labo, PRODUIT_CONCENTRATION),
            "numeroLot": LOT_CONCENTRATION, "quantite": UNITES_CONCENTRATION,
            "datePeremption": date(2028, 6, 30).isoformat()})
        assert r.status_code == 201, r.text
        with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
            series_concentration = [n[:-4] for n in archive.namelist()]

    with SessionLocal() as db:
        structures = {s.id: s for s in db.query(Structure).all()}
        utilisateur_de = {u.structure_id: u.id for u in db.query(Utilisateur).all()}
        lignes = db.query(Evenement, Utilisateur.structure_id).join(
            Utilisateur, Evenement.utilisateur_id == Utilisateur.id).all()
        existants = [(e.id, EvenementSimule(e.numeroSerie, e.typeOperation.value, e.dateHeure,
                                            e.latitude, e.longitude, structure_id))
                     for e, structure_id in lignes]

        # Position habituelle d'une structure: moyenne de ses evenements
        positions = defaultdict(list)
        for _, e in existants:
            positions[e.acteur_id].append((e.latitude, e.longitude))
        acteurs = {sid: Acteur(sid, structures[sid].type.value, structures[sid].localisation,
                               (float(np.mean([p[0] for p in pts])), float(np.mean([p[1] for p in pts]))))
                   for sid, pts in positions.items()}
        normal = [e for _, e in existants]

        # Anomalies de type unite
        deja: set[str] = set()
        injections = (injecter_reutilisations(normal, acteurs, PAR_TYPE, FIN, g, deja)
                      + injecter_ruptures(normal, acteurs, PAR_TYPE, FIN, g, deja)
                      + injecter_trajets(normal, acteurs, PAR_TYPE, FIN, g, deja))

        # Concentration: tout le lot est livre a une seule officine de Louga
        fabricant = next(a for a in acteurs.values() if a.type == "fabricant")
        grossistes = sorted((a for a in acteurs.values() if a.type == "grossisteRepartiteur"), key=lambda a: a.id)
        cible = next(a for a in acteurs.values() if a.type == "officine" and a.ville == VILLE_CONCENTRATION)
        srs = {a.ville: a for a in acteurs.values() if a.type == "SR"}
        lot = simuler_historique({LOT_CONCENTRATION: series_concentration}, fabricant, grossistes, srs,
                                 [cible], DEBUT_CONCENTRATION, FIN, g)
        receptions_cible = [e for e in lot if e.typeOperation == "reception" and e.acteur_id == cible.id]

        # Ecriture dans la base copiee et dans les fichiers de verite terrain
        etiquette: dict[EvenementSimule, str] = {i.evenement: i.type for i in injections}
        etiquette.update({e: "concentrationInhabituelle" for e in receptions_cible})
        nouveaux = [i.evenement for i in injections] + lot
        ids = {}
        for e in nouveaux:
            ids[e] = new_id()
            db.add(Evenement(id=ids[e], typeOperation=TypeOperation(e.typeOperation), dateHeure=e.dateHeure,
                             latitude=e.latitude, longitude=e.longitude, numeroSerie=e.numeroSerie,
                             utilisateur_id=utilisateur_de[e.acteur_id]))
        for e in nouveaux:
            if e.typeOperation == "dispensation":
                db.get(Unite, e.numeroSerie).statut = StatutUnite.desactivee
        db.commit()

        toutes = [(ident, e) for ident, e in existants] + [(ids[e], e) for e in nouveaux]
        toutes.sort(key=lambda t: t[1].dateHeure)
        champs = ["id", "numeroSerie", "typeOperation", "dateHeure", "latitude", "longitude",
                  "structure", "typeStructure", "ville", "etiquette"]
        with open(DOSSIER / "historique_anomalies.csv", "w", newline="", encoding="utf-8") as f:
            ecrivain = csv.DictWriter(f, fieldnames=champs)
            ecrivain.writeheader()
            for ident, e in toutes:
                a = acteurs[e.acteur_id]
                ecrivain.writerow({"id": ident, "numeroSerie": e.numeroSerie, "typeOperation": e.typeOperation,
                                   "dateHeure": e.dateHeure.isoformat(sep=" "), "latitude": round(e.latitude, 6),
                                   "longitude": round(e.longitude, 6), "structure": structures[e.acteur_id].nom,
                                   "typeStructure": a.type, "ville": a.ville,
                                   "etiquette": etiquette.get(e, "normal")})
        with open(DOSSIER / "anomalies_injectees.csv", "w", newline="", encoding="utf-8") as f:
            ecrivain = csv.writer(f)
            ecrivain.writerow(["typeAnomalie", "evenement_id", "numeroSerie", "dateHeure", "structure", "ville",
                               "description"])
            for i in injections:
                e = i.evenement
                ecrivain.writerow([i.type, ids[e], e.numeroSerie, e.dateHeure.isoformat(sep=" "),
                                   structures[e.acteur_id].nom, acteurs[e.acteur_id].ville, i.description])
            for e in receptions_cible:
                ecrivain.writerow(["concentrationInhabituelle", ids[e], e.numeroSerie,
                                   e.dateHeure.isoformat(sep=" "), structures[e.acteur_id].nom, cible.ville,
                                   f"{len(receptions_cible)} unites d'un meme lot recues d'un coup"])

        # Resume
        habituel = [e for _, e in existants if e.acteur_id == cible.id and e.typeOperation == "reception"]
        semaines = (FIN - datetime(2026, 8, 3)).days / 7
        print(f"{len(existants)} evenements normaux, {len(nouveaux)} ajoutes")
        for type_ in ("reutilisationIdentifiant", "ruptureSequence", "trajetInhabituel"):
            print(f"  {type_}: {sum(1 for i in injections if i.type == type_)}")
        print(f"  concentrationInhabituelle: {len(receptions_cible)} receptions a {cible.ville} "
              f"(volume habituel: environ {len(habituel) / semaines:.1f} receptions par semaine)")


if __name__ == "__main__":
    main()