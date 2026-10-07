"""Etape 31: historique normal du circuit (phase 3 de la methodologie).

Les structures, les produits, les lots et les unites sont crees par les vraies routes de
l'application. Seuls les evenements sont ecrits directement dans la base, car l'API date chaque
evenement du moment present et qu'il faut ici etaler les dates sur plusieurs semaines.
Tout va dans jeu_de_donnees/historique.db; tracabilite.db n'est pas touchee.

Lancer depuis la racine du projet:  python -m jeu_de_donnees.generer_historique
"""
import csv
import io
import os
import zipfile
from datetime import date, datetime
from pathlib import Path

DOSSIER = Path(__file__).parent
os.environ["DATABASE_URL"] = f"sqlite:///{(DOSSIER / 'historique.db').as_posix()}"

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.codes import cle_de_controle_gtin  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (Evenement, StatutUnite, Structure, TypeOperation,  # noqa: E402
                        Unite, Utilisateur, new_id)
from app.references import charger_references  # noqa: E402

from .geographie import VILLES  # noqa: E402
from .simulation import Acteur, simuler_historique  # noqa: E402

GRAINE = 31
MOT_DE_PASSE = "MotDePasseHistorique1"
DEBUT, FIN = datetime(2026, 8, 3, 8, 0), datetime(2026, 10, 5, 23, 59)
LOTS_PAR_PRODUIT, UNITES_PAR_LOT = 3, 50
PRODUITS = [("Paracetamol 500 mg", "Comprime", "Boite de 16", "0376000000201"),
            ("Amoxicilline 500 mg", "Gelule", "Boite de 12", "0376000000202"),
            ("Ibuprofene 400 mg", "Comprime", "Boite de 20", "0376000000203"),
            ("Metformine 850 mg", "Comprime", "Boite de 30", "0376000000204")]
# (reference, identifiant de connexion, ville) des structures qui s'inscrivent
GROSSISTES = [("JD-GRO-001", "gros.dakar", "Dakar"), ("JD-GRO-002", "gros.kaolack", "Kaolack")]
OFFICINES = [("JD-OFF-001", "off.dakar1", "Dakar"), ("JD-OFF-002", "off.dakar2", "Dakar"),
             ("JD-OFF-003", "off.dakar3", "Dakar"), ("JD-OFF-004", "off.thies1", "Thies"),
             ("JD-OFF-005", "off.thies2", "Thies"), ("JD-OFF-006", "off.saintlouis1", "Saint-Louis"),
             ("JD-OFF-007", "off.kaolack1", "Kaolack"), ("JD-OFF-008", "off.kaolack2", "Kaolack"),
             ("JD-OFF-009", "off.ziguinchor1", "Ziguinchor"), ("JD-OFF-010", "off.tamba1", "Tambacounda"),
             ("JD-OFF-011", "off.louga1", "Louga"), ("JD-OFF-012", "off.diourbel1", "Diourbel")]


def inscrire(client, nom, type_, ville, reference, login) -> None:
    r = client.post("/structures/inscription", json={
        "structure": {"nom": nom, "type": type_, "localisation": ville, "referenceAutorisation": reference},
        "responsable": {"nom": f"Responsable {nom}", "fonction": "Responsable",
                        "identifiantConnexion": login, "motDePasse": MOT_DE_PASSE}})
    assert r.status_code == 201, r.text


def entete(client, login) -> dict:
    r = client.post("/auth/connexion", data={"username": login, "password": MOT_DE_PASSE})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def identifiant_produit(client, entete_labo, nom) -> str:
    """Identifiant du produit enregistre sous ce nom (recherche par l'API)."""
    return next(p["id"] for p in client.get("/produits", headers=entete_labo, params={"q": nom}).json())


def main() -> None:
    (DOSSIER / "historique.db").unlink(missing_ok=True)
    g = np.random.default_rng(GRAINE)

    with TestClient(app) as client:
        with SessionLocal() as db:
            charger_references(db, DOSSIER / "references_jeu.csv")
        inscrire(client, "Laboratoire Historique", "fabricant", "Dakar", "JD-FAB-001", "labo.hist")
        for reference, login, ville in GROSSISTES:
            inscrire(client, f"Grossiste {ville}", "grossisteRepartiteur", ville, reference, login)
        inscrire(client, "Pharmacie Nationale d'Approvisionnement", "PNA", "Dakar", "JD-PNA-001", "pna.hist")
        for reference, login, ville in OFFICINES:
            inscrire(client, f"Officine {login}", "officine", ville, reference, login)

        # La PNA cree le compte chef des SR dont les villes ont une officine
        pna = entete(client, "pna.hist")
        sr_par_ville = {s["localisation"]: s["id"] for s in client.get("/sr", headers=pna).json()}
        for ville in sorted({v for _, _, v in OFFICINES}):
            r = client.post(f"/sr/{sr_par_ville[ville]}/responsable", headers=pna, json={
                "nom": f"Chef SR {ville}", "fonction": "Pharmacien chef",
                "identifiantConnexion": f"sr.{ville.lower()}", "motDePasse": MOT_DE_PASSE})
            assert r.status_code == 201, r.text

        # Le fabricant enregistre ses produits et serialise ses lots
        labo = entete(client, "labo.hist")
        lots: dict[str, list[str]] = {}
        for i, (nom, forme, cond, corps) in enumerate(PRODUITS, start=1):
            r = client.post("/produits", headers=labo, json={
                "nom": nom, "composition": nom, "formePharmaceutique": forme, "conditionnement": cond,
                "gtin": corps + str(cle_de_controle_gtin(corps))})
            assert r.status_code == 201, r.text
            produit_id = identifiant_produit(client, labo, nom)
            for j in range(1, LOTS_PAR_PRODUIT + 1):
                lot = f"HS-{i}{j:02d}"
                r = client.post("/lots/serialisation", headers=labo, json={
                    "produit_id": produit_id, "numeroLot": lot,
                    "quantite": UNITES_PAR_LOT, "datePeremption": date(2028, 6, 30).isoformat()})
                assert r.status_code == 201, r.text
                with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
                    lots[lot] = [n[:-4] for n in archive.namelist()]

    # Acteurs de la simulation: structure, ville, position habituelle (centre-ville + decalage fixe)
    with SessionLocal() as db:
        def acteur(login: str, type_: str, ville: str) -> Acteur:
            u = db.query(Utilisateur).filter_by(identifiantConnexion=login).one()
            base = VILLES[ville]
            position = (base[0] + float(g.uniform(-0.03, 0.03)), base[1] + float(g.uniform(-0.03, 0.03)))
            return Acteur(u.structure_id, type_, ville, position)

        fabricant = acteur("labo.hist", "fabricant", "Dakar")
        grossistes = [acteur(login, "grossisteRepartiteur", ville) for _, login, ville in GROSSISTES]
        srs = {ville: acteur(f"sr.{ville.lower()}", "SR", ville) for ville in sorted({v for _, _, v in OFFICINES})}
        officines = [acteur(login, "officine", ville) for _, login, ville in OFFICINES]
        tous = {a.id: a for a in [fabricant, *grossistes, *srs.values(), *officines]}

        evenements = simuler_historique(lots, fabricant, grossistes, srs, officines, DEBUT, FIN, g)

        utilisateur_de = {u.structure_id: u.id for u in db.query(Utilisateur).all()}
        nom_de = {s.id: s.nom for s in db.query(Structure).all()}
        lignes, dispensees = [], set()
        for e in evenements:
            ident = new_id()
            db.add(Evenement(id=ident, typeOperation=TypeOperation(e.typeOperation), dateHeure=e.dateHeure,
                             latitude=e.latitude, longitude=e.longitude, numeroSerie=e.numeroSerie,
                             utilisateur_id=utilisateur_de[e.acteur_id]))
            if e.typeOperation == "dispensation":
                dispensees.add(e.numeroSerie)
            lignes.append({"id": ident, "numeroSerie": e.numeroSerie, "typeOperation": e.typeOperation,
                           "dateHeure": e.dateHeure.isoformat(sep=" "), "latitude": round(e.latitude, 6),
                           "longitude": round(e.longitude, 6), "structure": nom_de[e.acteur_id],
                           "typeStructure": tous[e.acteur_id].type, "ville": tous[e.acteur_id].ville,
                           "etiquette": "normal"})
        for serie in dispensees:
            db.get(Unite, serie).statut = StatutUnite.desactivee
        db.commit()
        total_unites = db.query(Unite).count()

    with open(DOSSIER / "historique_evenements.csv", "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.DictWriter(f, fieldnames=list(lignes[0]))
        ecrivain.writeheader()
        ecrivain.writerows(lignes)
    print(f"{total_unites} unites, {len(lignes)} evenements normaux, {len(dispensees)} unites dispensees")
    print(f"Periode: {lignes[0]['dateHeure']} a {lignes[-1]['dateHeure']}")
    for operation in ("expedition", "reception", "dispensation"):
        print(f"  {operation}: {sum(1 for l in lignes if l['typeOperation'] == operation)}")


if __name__ == "__main__":
    main()