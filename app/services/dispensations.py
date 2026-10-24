"""Enregistrement de la dispensation d'une unite au patient (fiche 8): regles metier, sans rien savoir d'HTTP."""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.domaine.models import (Anomalie, Evenement, StatutUnite, TypeAnomalie, TypeOperation,
                                TypeStructure, Unite, Utilisateur)
from app.services.contenant import conteneur_actif_de_la_boite
from app.services.erreurs import ErreurMetier
from app.services.horsligne import date_de_l_operation

MESSAGE_REUTILISATION = ("Dispensation non validee: cet identifiant est deja desactive. "
                         "Reutilisation possible, une alerte est soumise a verification.")


@dataclass(frozen=True)
class ResultatDispensation:
    evenement: Evenement
    message: str
    type_anomalie: str | None   # "ruptureSequence", "boiteHorsCarton" ou None

    @property
    def alerte(self) -> bool:
        return self.type_anomalie is not None


def _receptionnee_par(db: Session, numero_serie: str, structure_id: str) -> bool:
    """Vrai si l'historique de l'unite contient une reception faite par cette structure."""
    return db.query(Evenement).join(Utilisateur, Evenement.utilisateur_id == Utilisateur.id).filter(
        Evenement.numeroSerie == numero_serie,
        Evenement.typeOperation == TypeOperation.reception,
        Utilisateur.structure_id == structure_id).first() is not None


def verifier_officine(utilisateur: Utilisateur) -> None:
    if utilisateur.structure.type != TypeStructure.officine:
        raise ErreurMetier(403, "La dispensation est reservee aux officines.")


def enregistrer_dispensation(db: Session, utilisateur: Utilisateur, unite: Unite, latitude: float | None,
                             longitude: float | None, date_heure: datetime | None,
                             identifiant_client: str | None) -> ResultatDispensation:
    """Cree l'evenement de dispensation et desactive definitivement l'identifiant.

    Variante 3b: identifiant deja desactive. Reutilisation possible: la dispensation n'est pas validee,
    l'evenement est garde avec une alerte a verifier (ErreurMetier 409). Variante 3c: aucune reception par
    cette officine dans l'historique (rupture de sequence): la dispensation se poursuit, sous reserve de
    verification. Agregation: boite encore dans un carton non ouvert (alerte "boite hors carton")."""
    evenement = Evenement(typeOperation=TypeOperation.dispensation, latitude=latitude,
                          longitude=longitude, numeroSerie=unite.numeroSerie,
                          utilisateur_id=utilisateur.id, dateHeure=date_de_l_operation(date_heure),
                          identifiantClient=identifiant_client)
    db.add(evenement)

    if unite.statut == StatutUnite.desactivee:
        db.add(Anomalie(typeAnomalie=TypeAnomalie.reutilisationIdentifiant, score=1.0, evenement=evenement))
        db.commit()
        raise ErreurMetier(409, MESSAGE_REUTILISATION)

    rupture = not _receptionnee_par(db, unite.numeroSerie, utilisateur.structure_id)
    if rupture:
        db.add(Anomalie(typeAnomalie=TypeAnomalie.ruptureSequence, score=1.0, evenement=evenement))
    hors_carton = conteneur_actif_de_la_boite(db, unite.numeroSerie) is not None
    if hors_carton:
        db.add(Anomalie(typeAnomalie=TypeAnomalie.boiteHorsCarton, score=1.0, evenement=evenement))

    unite.statut = StatutUnite.desactivee
    db.commit()
    db.refresh(evenement)

    if rupture:
        message = ("Dispensation enregistree avec une alerte: aucune reception par cette officine "
                   "dans l'historique, a verifier.")
    elif hors_carton:
        message = ("Dispensation enregistree avec une alerte: cette boite est encore dans un carton non ouvert, "
                   "ouvrez le carton d'abord, a verifier.")
    else:
        message = "Dispensation enregistree."
    return ResultatDispensation(evenement, message,
                                "ruptureSequence" if rupture else ("boiteHorsCarton" if hors_carton else None))
