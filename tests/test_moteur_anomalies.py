"""Tests du moteur d'anomalies (phase 5): reutilisation, rupture de sequence, trajet inhabituel, concentration."""
import time
from datetime import datetime, timedelta

from app.models import Anomalie, TypeAnomalie, TypeOperation, TypeStructure, Unite
from app.moteur_anomalies import (DISTANCE_MIN_KM, LOTS_MIN, VITESSE_MAX_KMH, Z_MAX, Detection, Operation,
                                  analyser_base, analyser_unite, charger_operations, detecter_concentrations,
                                  enregistrer, est_trajet_inhabituel, lancer_analyse, score_concentration)
from jeu_de_donnees.evaluer_anomalies import comparer, groupes
from jeu_de_donnees.simulation import simuler_historique
from tests.test_anomalies import DEBUT, FIN, injecter, monde
from tests.test_dispensations import preparer
from tests.test_evenements import session

T0 = datetime(2026, 9, 1, 8, 0)
REUTILISATION, RUPTURE = TypeAnomalie.reutilisationIdentifiant, TypeAnomalie.ruptureSequence
TRAJET = TypeAnomalie.trajetInhabituel
DAKAR, PROCHE, ZIGUINCHOR = (14.6937, -17.4441), (14.70, -17.30), (12.5833, -16.2719)   # Dakar-Proche 16 km, Dakar-Ziguinchor 267 km


def pause():
    """Laisse passer assez de temps pour que deux appels de l'API aient des dates differentes.

    Sous Windows l'horloge avance par pas d'environ 15 ms: sans pause, deux evenements consecutifs peuvent
    avoir exactement la meme date, et leur ordre n'est alors plus determine (le moteur departage par identifiant)."""
    time.sleep(0.05)


def op(numero, type_, minutes, structure, ident=None, position=None):
    latitude, longitude = position if position else (None, None)
    return Operation(ident or f"{numero}-{type_.value}-{minutes}-{structure}", numero, type_,
                     T0 + timedelta(minutes=minutes), structure, latitude, longitude)


def types(detections):
    return [d.type for d in detections]


def test_une_chaine_normale_ne_signale_rien():
    chaine = [op("S1", TypeOperation.expedition, 0, "fab"),
              op("S1", TypeOperation.reception, 10, "gros"), op("S1", TypeOperation.expedition, 20, "gros"),
              op("S1", TypeOperation.reception, 30, "off"), op("S1", TypeOperation.dispensation, 40, "off")]
    assert analyser_unite(chaine) == []


def test_un_evenement_apres_la_dispensation_est_une_reutilisation():
    base = [op("S1", TypeOperation.reception, 0, "off"), op("S1", TypeOperation.dispensation, 10, "off")]
    for type_ in TypeOperation:
        detections = analyser_unite(base + [op("S1", type_, 20, "autre", "dernier")])
        assert [(d.evenement_id, d.type) for d in detections] == [("dernier", REUTILISATION)]


def test_une_dispensation_sans_reception_par_la_meme_structure_est_une_rupture():
    sans_reception = [op("S1", TypeOperation.dispensation, 10, "off", "d")]
    assert [(d.evenement_id, d.type) for d in analyser_unite(sans_reception)] == [("d", RUPTURE)]
    recue_ailleurs = [op("S1", TypeOperation.reception, 0, "autre"), op("S1", TypeOperation.dispensation, 10, "off", "d")]
    assert types(analyser_unite(recue_ailleurs)) == [RUPTURE]
    recue_ici = [op("S1", TypeOperation.reception, 0, "off"), op("S1", TypeOperation.dispensation, 10, "off")]
    assert analyser_unite(recue_ici) == []


def test_une_reutilisation_n_est_pas_signalee_en_plus_comme_rupture():
    # deuxieme dispensation par une structure qui n'a jamais recu l'unite: reutilisation seulement
    histoire = [op("S1", TypeOperation.reception, 0, "a"), op("S1", TypeOperation.dispensation, 10, "a"),
                op("S1", TypeOperation.dispensation, 20, "b", "second")]
    assert [(d.evenement_id, d.type) for d in analyser_unite(histoire)] == [("second", REUTILISATION)]


def test_l_ordre_de_la_liste_ne_compte_pas_seul_le_temps_compte():
    desordre = [op("S1", TypeOperation.dispensation, 10, "off"), op("S1", TypeOperation.reception, 0, "off")]
    assert analyser_unite(desordre) == []


def test_le_moteur_retrouve_exactement_les_anomalies_injectees_dans_la_simulation():
    normal, acteurs, injections = injecter()

    def detecter(evenements):
        """Couples (type, evenement) signales par le moteur sur une liste d'evenements simules."""
        par_id, par_unite = {}, {}
        for i, e in enumerate(evenements):
            par_id[str(i)] = e
            par_unite.setdefault(e.numeroSerie, []).append(Operation(
                str(i), e.numeroSerie, TypeOperation(e.typeOperation), e.dateHeure, e.acteur_id,
                e.latitude, e.longitude))
        return {(d.type.value, par_id[d.evenement_id]) for ops in par_unite.values() for d in analyser_unite(ops)}

    assert detecter(normal) == set()
    attendu = {(i.type, i.evenement) for i in injections}
    assert len(attendu) == 12            # 4 reutilisations, 4 ruptures, 4 trajets
    assert detecter(normal + [i.evenement for i in injections]) == attendu


def test_un_trajet_trop_rapide_est_signale_a_l_evenement_d_arrivee():
    histoire = [op("S1", TypeOperation.reception, 0, "off1", position=DAKAR),
                op("S1", TypeOperation.reception, 30, "off2", "arrivee", position=ZIGUINCHOR)]   # 267 km en 30 min
    detections = analyser_unite(histoire)
    assert [(d.evenement_id, d.type) for d in detections] == [("arrivee", TRAJET)]
    assert "267 km" in detections[0].description and "30 min" in detections[0].description


def test_un_trajet_plausible_ou_court_ou_sans_position_n_est_pas_signale():
    # 267 km en 8 h: 33 km/h
    assert analyser_unite([op("S1", TypeOperation.reception, 0, "a", position=DAKAR),
                           op("S1", TypeOperation.reception, 480, "b", position=ZIGUINCHOR)]) == []
    # 16 km en 2 minutes: rapide, mais sous la distance minimale
    assert analyser_unite([op("S1", TypeOperation.reception, 0, "a", position=DAKAR),
                           op("S1", TypeOperation.reception, 2, "b", position=PROCHE)]) == []
    # le deuxieme evenement n'a pas de position: rien a comparer
    assert analyser_unite([op("S1", TypeOperation.reception, 0, "a", position=DAKAR),
                           op("S1", TypeOperation.reception, 5, "b")]) == []


def test_un_evenement_sans_position_est_ignore_et_on_relie_les_deux_positions_connues():
    histoire = [op("S1", TypeOperation.reception, 0, "a", position=DAKAR),
                op("S1", TypeOperation.expedition, 10, "a"),
                op("S1", TypeOperation.reception, 30, "b", "arrivee", position=ZIGUINCHOR)]
    assert [(d.evenement_id, d.type) for d in analyser_unite(histoire)] == [("arrivee", TRAJET)]


def test_les_limites_du_trajet_inhabituel():
    assert not est_trajet_inhabituel(DISTANCE_MIN_KM - 0.1, 0.001)                 # trop court pour compter
    assert est_trajet_inhabituel(DISTANCE_MIN_KM, 0.0)                             # meme instant, lieux differents
    assert not est_trajet_inhabituel(VITESSE_MAX_KMH, 1.0)                         # exactement au maximum: normal
    assert est_trajet_inhabituel(VITESSE_MAX_KMH + 1, 1.0)


def test_un_meme_evenement_peut_reveler_une_reutilisation_et_un_trajet():
    histoire = [op("S1", TypeOperation.reception, 0, "off", position=DAKAR),
                op("S1", TypeOperation.dispensation, 10, "off", position=DAKAR),
                op("S1", TypeOperation.reception, 20, "autre", "dernier", position=ZIGUINCHOR)]
    assert sorted(d.type.value for d in analyser_unite(histoire)) == [REUTILISATION.value, TRAJET.value]


def test_le_moteur_est_d_accord_avec_les_alertes_de_l_application(client):
    """Les memes scenarios, joues par l'API puis relus par le moteur, donnent les memes anomalies."""
    serie, _, officine = preparer(client)                                   # reception par l'officine
    pause()
    assert client.post("/dispensations", headers=officine, data={"numeroSerie": serie}).status_code == 201
    pause()
    assert client.post("/dispensations", headers=officine, data={"numeroSerie": serie}).status_code == 409
    pause()
    assert client.post("/evenements", headers=officine,
                       data={"typeOperation": "reception", "numeroSerie": serie}).status_code == 201
    autre = session(client).query(Unite).filter(Unite.numeroSerie != serie).first().numeroSerie
    pause()
    assert client.post("/dispensations", headers=officine, data={"numeroSerie": autre}).status_code == 201  # rupture

    db = session(client)
    de_l_application = {(a.typeAnomalie, a.evenement_id) for a in db.query(Anomalie).all()}
    du_moteur = {(d.type, d.evenement_id) for d in analyser_base(db)}
    assert {t for t, _ in du_moteur} == {REUTILISATION, RUPTURE} and len(du_moteur) == 3
    assert du_moteur == de_l_application


def test_comparer_calcule_precision_et_rappel_par_type():
    detections = [Detection("e1", "S1", REUTILISATION, 1.0, ""), Detection("e2", "S2", REUTILISATION, 1.0, ""),
                  Detection("e3", "S3", RUPTURE, 1.0, "")]
    verite = {(REUTILISATION.value, "e1"), (REUTILISATION.value, "e9"), (RUPTURE.value, "e3")}
    lignes = {l["type"]: l for l in comparer(detections, verite, [REUTILISATION.value, RUPTURE.value, "trajetInhabituel"])}
    assert (lignes[REUTILISATION.value]["vraisPositifs"], lignes[REUTILISATION.value]["faussesAlertes"],
            lignes[REUTILISATION.value]["manquees"]) == (1, 1, 1)
    assert lignes[REUTILISATION.value]["precision"] == 0.5 and lignes[REUTILISATION.value]["rappel"] == 0.5
    assert lignes[RUPTURE.value]["precision"] == 1.0 and lignes[RUPTURE.value]["rappel"] == 1.0
    assert lignes["trajetInhabituel"]["precision"] == "" and lignes["trajetInhabituel"]["manquees"] == 0


# ---- Concentration inhabituelle ----
CONCENTRATION = TypeAnomalie.concentrationInhabituelle


def receptions(structure, lot, quantite, type_=TypeStructure.officine):
    """`quantite` unites du lot `lot` recues par `structure`."""
    return [Operation(f"{structure}-{lot}-{i}", f"{lot}-{i}", TypeOperation.reception, T0 + timedelta(minutes=i),
                      structure, None, None, lot, type_, lot) for i in range(quantite)]


def historique(structure, quantites, **kw):
    """Une officine qui a recu les lots l0, l1, ... avec ces quantites."""
    return [o for i, q in enumerate(quantites) for o in receptions(structure, f"l{i}", q, **kw)]


HABITUEL = [3, 4, 5, 4, 3, 5]    # mediane 4, MAD 1


def test_un_lot_tres_au_dessus_de_l_habitude_de_l_officine_est_signale_sur_toutes_ses_receptions():
    detections = detecter_concentrations(historique("off", HABITUEL + [40]))
    assert len(detections) == 40 and {d.type for d in detections} == {CONCENTRATION}
    assert {d.groupe for d in detections} == {"off/l6"}
    assert {d.evenement_id for d in detections} == {f"off-l6-{i}" for i in range(40)}
    assert all(0.5 < d.score <= 1 for d in detections)
    assert "40 unites du lot l6" in detections[0].description and "contre 4 " in detections[0].description


def test_des_variations_normales_ou_un_manque_ne_sont_pas_signales():
    assert detecter_concentrations(historique("off", HABITUEL + [8])) == []      # z = 2,7
    assert detecter_concentrations(historique("off", HABITUEL + [1])) == []      # en dessous: pas une concentration
    assert detecter_concentrations(historique("off", HABITUEL + [4])) == []


def test_le_seuil_est_sur_le_z_score_modifie():
    # mediane 4 et MAD 1: z = 0,6745 * (q - 4); seuil 3,5 donc q > 9,19
    assert detecter_concentrations(historique("off", HABITUEL + [9])) == []
    assert len(detecter_concentrations(historique("off", HABITUEL + [10]))) == 10
    assert score_concentration(Z_MAX) == 0.5 and score_concentration(1000) > 0.99


def test_chaque_officine_est_jugee_selon_sa_propre_habitude():
    gros = historique("gros-client", [30, 32, 28, 31, 29, 30, 34])
    petit = historique("petit-client", HABITUEL + [34])
    detections = detecter_concentrations(gros + petit)
    assert {d.groupe for d in detections} == {"petit-client/l6"}


def test_une_officine_sans_assez_d_historique_n_est_pas_jugee():
    assert LOTS_MIN == 5
    assert detecter_concentrations(historique("off", [3, 4, 5, 4] + [40])) == []        # 4 autres lots seulement
    assert len(detecter_concentrations(historique("off", [3, 4, 5, 4, 3] + [40]))) == 40  # 5 autres lots


def test_si_tous_les_lots_sont_identiques_la_dispersion_ne_tombe_pas_a_zero():
    assert detecter_concentrations(historique("off", [4] * 6 + [5])) == []              # z = 0,67
    assert len(detecter_concentrations(historique("off", [4] * 6 + [10]))) == 10         # z = 4,05


def test_seules_les_receptions_des_officines_sont_jugees():
    assert detecter_concentrations(historique("gros", HABITUEL + [40], type_=TypeStructure.grossisteRepartiteur)) == []
    sans_lot = [Operation(o.id, o.numeroSerie, o.type, o.dateHeure, o.structure_id, None, None)
                for o in historique("off", HABITUEL + [40])]
    assert detecter_concentrations(sans_lot) == []
    autres_operations = [Operation(f"x{i}", f"u{i}", TypeOperation.dispensation, T0, "off", None, None,
                                   "gros-lot", TypeStructure.officine) for i in range(60)]
    assert detecter_concentrations(historique("off", HABITUEL) + autres_operations) == []


def test_une_unite_recue_deux_fois_compte_une_fois_mais_ses_deux_evenements_sont_signales():
    base = historique("off", HABITUEL + [10])
    doublon = Operation("double", "l6-0", TypeOperation.reception, T0 + timedelta(days=1), "off", None, None,
                        "l6", TypeStructure.officine, "l6")
    detections = detecter_concentrations(base + [doublon])
    assert len(detections) == 11 and "10 unites" in detections[0].description


def test_la_concentration_simulee_est_retrouvee_et_domine_les_alertes():
    normal, acteurs, g = monde()
    destinataire = acteurs["o-Thies"]
    lot = {"CONC": [f"CONCU{j:03d}" for j in range(80)]}
    srs = {v: a for v, a in ((k.split("-")[1], a) for k, a in acteurs.items() if k.startswith("sr-"))}
    injecte = simuler_historique(lot, acteurs["fab"], [acteurs["g1"]], srs, [destinataire], DEBUT, FIN, g)

    def detecter(evenements):
        ops = [Operation(str(i), e.numeroSerie, TypeOperation(e.typeOperation), e.dateHeure, e.acteur_id,
                         e.latitude, e.longitude, e.numeroSerie.split("U")[0], TypeStructure(acteurs[e.acteur_id].type))
               for i, e in enumerate(evenements)]
        return detecter_concentrations(ops)

    # Ce petit monde (8 lots, 6 officines) donne peu de recul: une alerte faible peut y apparaitre
    # (un lot de 11 unites contre 5 d'habitude, z = 4,0). La concentration injectee, elle, domine.
    assert {d.groupe for d in detecter(normal)} <= {"o-Saint-Louis/L7"}
    trouvees = detecter(normal + injecte)
    receptions_thies = [e for e in injecte if e.acteur_id == "o-Thies" and e.typeOperation == "reception"]
    injectees = [d for d in trouvees if d.groupe == "o-Thies/CONC"]
    assert len(injectees) == len(receptions_thies) == 80
    assert min(d.score for d in injectees) > max([d.score for d in trouvees if d.groupe != "o-Thies/CONC"] or [0])


def test_le_chargement_depuis_la_base_donne_le_lot_et_le_type_de_structure(client):
    serie, _, officine = preparer(client)
    operations = [o for ops in charger_operations(session(client)).values() for o in ops]
    reception = next(o for o in operations if o.numeroSerie == serie and o.type == TypeOperation.reception
                     and o.structure_type == TypeStructure.officine)
    assert reception.lot_id == session(client).get(Unite, serie).lot_id and reception.numeroLot


def test_groupes_compte_une_alerte_par_structure_et_lot():
    detections = [Detection(f"e{i}", f"S{i}", CONCENTRATION, 0.9, "", "off/l1") for i in range(5)]
    detections.append(Detection("x", "Sx", REUTILISATION, 1.0, "", None))
    assert groupes(detections) == {"off/l1"}


# ---- Ecriture dans la table des anomalies ----
def test_lancer_analyse_ne_double_pas_les_anomalies_deja_enregistrees_par_l_api(client):
    serie, _, officine = preparer(client)
    pause()
    assert client.post("/dispensations", headers=officine, data={"numeroSerie": serie}).status_code == 201
    pause()
    assert client.post("/dispensations", headers=officine, data={"numeroSerie": serie}).status_code == 409
    db = session(client)
    avant = db.query(Anomalie).count()
    assert avant == 1                                    # la reutilisation, ecrite par l'API
    assert lancer_analyse(db) == (1, 0)                  # le moteur la retrouve, n'ajoute rien
    assert db.query(Anomalie).count() == 1


def test_lancer_analyse_ecrit_les_anomalies_nouvelles_une_seule_fois(client):
    serie, _, officine = preparer(client)
    for latitude, longitude in (("14.6937", "-17.4441"), ("12.5833", "-16.2719")):   # Dakar puis Ziguinchor, a la suite
        pause()
        assert client.post("/evenements", headers=officine, data={
            "typeOperation": "reception", "numeroSerie": serie,
            "latitude": latitude, "longitude": longitude}).status_code == 201
    db = session(client)
    assert db.query(Anomalie).count() == 0               # l'API ne connait pas la regle du trajet
    detections, ajoutees = lancer_analyse(db)
    assert (detections, ajoutees) == (1, 1)
    anomalie = db.query(Anomalie).one()
    assert anomalie.typeAnomalie == TRAJET and anomalie.score == 1.0 and anomalie.statut == "a_verifier"
    assert lancer_analyse(db) == (1, 0)                  # relancer ne cree pas de doublon
    assert db.query(Anomalie).count() == 1


def test_enregistrer_ignore_les_doublons_dans_la_liste_elle_meme(client):
    serie, _, _ = preparer(client)
    db = session(client)
    reception = charger_operations(db)[serie][0]
    d = Detection(reception.id, serie, CONCENTRATION, 0.9, "", "g")
    assert enregistrer(db, [d, d]) == 1