"""Tests des alertes regroupees: la concentration est une seule alerte, les autres anomalies restent une par une."""
from datetime import date, timedelta

from app.alertes import alertes_regroupees
from app.models import (Anomalie, Evenement, Lot, ReferenceAutorisation, TypeAnomalie, TypeOperation, TypeStructure,
                        Unite, Utilisateur)
from tests.test_evenements import inscrire_structure, serialiser, session

CONCENTRATION, REUTILISATION = TypeAnomalie.concentrationInhabituelle, TypeAnomalie.reutilisationIdentifiant


def expedier(db, series):
    """Le fabricant a expedie ces unites (evenements ecrits en base): sans cela, chaque reception serait une rupture."""
    fabricant = db.query(Utilisateur).filter(Utilisateur.identifiantConnexion == "awa.diop").one()
    db.add_all([Evenement(typeOperation=TypeOperation.expedition, numeroSerie=s, utilisateur_id=fabricant.id)
                for s in series])
    db.commit()


def receptions(db):
    return db.query(Evenement).filter(Evenement.typeOperation == TypeOperation.reception).order_by(Evenement.dateHeure).all()


def recevoir(client, entete, series):
    for serie in series:
        assert client.post("/evenements", headers=entete,
                           data={"typeOperation": "reception", "numeroSerie": serie}).status_code == 201


def test_une_concentration_de_plusieurs_evenements_est_une_seule_alerte(client):
    images, _ = serialiser(client, quantite=5)
    series = list(images)
    officine = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    db = session(client)
    expedier(db, series)
    recevoir(client, officine, series[:4])
    evenements = receptions(db)
    for e in evenements:
        db.add(Anomalie(typeAnomalie=CONCENTRATION, score=0.8, evenement_id=e.id))
    db.add(Anomalie(typeAnomalie=REUTILISATION, score=1.0, evenement_id=evenements[0].id))
    db.commit()

    assert db.query(Anomalie).count() == 5                       # 4 lignes de concentration + 1 reutilisation
    alertes = alertes_regroupees(db)
    assert len(alertes) == 2
    conc = next(a for a in alertes if a.typeAnomalie == CONCENTRATION)
    assert conc.evenements == 4 and conc.numeroSerie is None and conc.numeroLot and conc.score == 0.8
    assert conc.statut == "a_verifier"
    autre = next(a for a in alertes if a.typeAnomalie == REUTILISATION)
    assert autre.evenements == 1 and autre.numeroSerie == evenements[0].numeroSerie


def second_lot(db, produit_id, series):
    """Un deuxieme lot du meme produit, cree directement en base pour le test."""
    lot = Lot(numeroLot="LOT2026B", datePeremption=date.today() + timedelta(days=400), quantite=len(series),
              produit_id=produit_id)
    db.add(lot)
    db.flush()
    db.add_all([Unite(numeroSerie=s, lot_id=lot.id) for s in series])
    db.commit()


def test_deux_officines_ou_deux_lots_font_des_alertes_distinctes(client):
    premier, _ = serialiser(client, quantite=3)
    db = session(client)
    second_lot(db, db.query(Lot).one().produit_id, ["B-1", "B-2"])
    db.add(ReferenceAutorisation(reference="TEST-OFF-002", nom="Autre officine", type=TypeStructure.officine))
    db.commit()
    a = inscrire_structure(client, "officine", "TEST-OFF-001", "pharma1")
    b = inscrire_structure(client, "officine", "TEST-OFF-002", "pharma2")
    expedier(db, list(premier) + ["B-1", "B-2"])
    recevoir(client, a, list(premier)[:2] + ["B-1", "B-2"])
    recevoir(client, b, list(premier)[2:])
    for e in receptions(db):
        db.add(Anomalie(typeAnomalie=CONCENTRATION, score=0.9, evenement_id=e.id))
    db.commit()
    alertes = alertes_regroupees(db)
    assert sorted(x.evenements for x in alertes) == [1, 2, 2]     # (a, lot A) x2, (a, lot B) x2, (b, lot A) x1
    assert {x.numeroLot for x in alertes} == {"LOT2026A", "LOT2026B"}


def test_la_lecture_ne_modifie_rien_et_sans_anomalie_il_n_y_a_pas_d_alerte(client):
    images, _ = serialiser(client, quantite=2)
    assert alertes_regroupees(session(client)) == []
    db = session(client)
    avant = db.query(Anomalie).count()
    alertes_regroupees(db)
    assert db.query(Anomalie).count() == avant
