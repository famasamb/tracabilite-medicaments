"""Tests des regles du diagramme de classes."""
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (Structure, Utilisateur, Produit, Lot, Unite, Evenement,
                        Anomalie, TypeStructure, Role, StatutUnite,
                        TypeOperation, TypeAnomalie)


# ---------- Petites fonctions pour fabriquer des objets de test ----------

def une_structure(type_=TypeStructure.fabricant, nom="Structure test"):
    return Structure(nom=nom, type=type_, localisation="Dakar")


def un_utilisateur(structure, identifiant, role=Role.employe):
    return Utilisateur(nom=identifiant, fonction="test", identifiantConnexion=identifiant,
                       motDePasse="empreinte", role=role, structure=structure)


def un_produit(gtin=None, nom="Produit test"):
    return Produit(gtin=gtin, nom=nom, laboratoire="Labo", composition="substance",
                   formePharmaceutique="comprime", conditionnement="boite de 10")


def un_lot(produit, numero="LOT1", series=("S1",)):
    return Lot(numeroLot=numero, datePeremption=date(2028, 1, 1), quantite=len(series),
               produit=produit, unites=[Unite(numeroSerie=s) for s in series])


# ---------- Structure ----------

def test_une_pna_a_des_sr_comme_filiales(db):
    pna = une_structure(TypeStructure.PNA, "PNA")
    sr = Structure(nom="SR Thies", type=TypeStructure.SR, localisation="Thies", mere=pna)
    db.add_all([pna, sr])
    db.commit()
    assert [f.nom for f in pna.filiales] == ["SR Thies"]
    assert sr.mere.nom == "PNA"


# ---------- Utilisateur ----------

def test_un_responsable_et_plusieurs_employes(db):
    s = une_structure()
    db.add_all([s, un_utilisateur(s, "resp", Role.responsable),
                un_utilisateur(s, "emp1"), un_utilisateur(s, "emp2")])
    db.commit()
    assert len(s.utilisateurs) == 3


def test_deux_responsables_dans_une_structure_sont_refuses(db):
    s = une_structure()
    db.add_all([s, un_utilisateur(s, "resp1", Role.responsable)])
    db.commit()
    db.add(un_utilisateur(s, "resp2", Role.responsable))
    with pytest.raises(IntegrityError):
        db.commit()


def test_deux_structures_ont_chacune_leur_responsable(db):
    s1, s2 = une_structure(nom="A"), une_structure(nom="B")
    db.add_all([s1, s2, un_utilisateur(s1, "r1", Role.responsable),
                un_utilisateur(s2, "r2", Role.responsable)])
    db.commit()


def test_identifiant_de_connexion_unique(db):
    s = une_structure()
    db.add_all([s, un_utilisateur(s, "dupont")])
    db.commit()
    db.add(un_utilisateur(s, "dupont"))
    with pytest.raises(IntegrityError):
        db.commit()


# ---------- Produit ----------

def test_deux_produits_sans_gtin_sont_possibles(db):
    db.add_all([un_produit(nom="A"), un_produit(nom="B")])
    db.commit()


def test_gtin_unique_quand_il_est_renseigne(db):
    db.add(un_produit(gtin="03400930000120"))
    db.commit()
    db.add(un_produit(gtin="03400930000120", nom="Autre"))
    with pytest.raises(IntegrityError):
        db.commit()


# ---------- Lot et Unite ----------

def test_un_lot_contient_ses_unites_actives(db):
    p = un_produit()
    lot = un_lot(p, series=("S1", "S2", "S3"))
    db.add_all([p, lot])
    db.commit()
    assert len(lot.unites) == 3
    assert all(u.statut == StatutUnite.active for u in lot.unites)


def test_meme_numero_de_lot_refuse_pour_un_produit(db):
    p = un_produit()
    db.add_all([p, un_lot(p, "LOT1", ("S1",))])
    db.commit()
    db.add(un_lot(p, "LOT1", ("S2",)))
    with pytest.raises(IntegrityError):
        db.commit()


def test_meme_numero_de_lot_accepte_pour_deux_produits(db):
    p1, p2 = un_produit(nom="A"), un_produit(nom="B")
    db.add_all([p1, p2, un_lot(p1, "LOT1", ("S1",)), un_lot(p2, "LOT1", ("S2",))])
    db.commit()


def test_numero_de_serie_unique_dans_tout_le_systeme(db):
    p = un_produit()
    db.add_all([p, un_lot(p, "LOT1", ("S1",))])
    db.commit()
    db.add(un_lot(p, "LOT2", ("S1",)))
    with pytest.raises(IntegrityError):
        db.commit()


def test_supprimer_un_lot_supprime_ses_unites(db):
    p = un_produit()
    lot = un_lot(p, series=("S1", "S2"))
    db.add_all([p, lot])
    db.commit()
    db.delete(lot)
    db.commit()
    assert db.query(Unite).count() == 0


# ---------- Evenement et Anomalie ----------

def test_historique_d_une_unite_dans_l_ordre(db):
    s = une_structure()
    u = un_utilisateur(s, "emp")
    p = un_produit()
    lot = un_lot(p)
    db.add_all([s, u, p, lot])
    db.flush()
    db.add_all([
        Evenement(typeOperation=TypeOperation.expedition, numeroSerie="S1", utilisateur=u),
        Evenement(typeOperation=TypeOperation.reception, numeroSerie="S1", utilisateur=u,
                  latitude=14.69, longitude=-17.44),
    ])
    db.commit()
    unite = db.get(Unite, "S1")
    assert len(unite.evenements) == 2


def test_un_evenement_peut_reveler_une_anomalie(db):
    s = une_structure()
    u = un_utilisateur(s, "emp")
    p = un_produit()
    lot = un_lot(p)
    db.add_all([s, u, p, lot])
    db.flush()
    e = Evenement(typeOperation=TypeOperation.dispensation, numeroSerie="S1", utilisateur=u)
    e.anomalies.append(Anomalie(typeAnomalie=TypeAnomalie.reutilisationIdentifiant, score=0.95))
    db.add(e)
    db.commit()
    assert e.anomalies[0].typeAnomalie == TypeAnomalie.reutilisationIdentifiant
    assert 0 <= e.anomalies[0].score <= 1


def test_evenement_sur_une_unite_inconnue_refuse(db):
    s = une_structure()
    u = un_utilisateur(s, "emp")
    db.add_all([s, u])
    db.commit()
    db.add(Evenement(typeOperation=TypeOperation.reception, numeroSerie="INCONNU", utilisateur=u))
    with pytest.raises(IntegrityError):
        db.commit()