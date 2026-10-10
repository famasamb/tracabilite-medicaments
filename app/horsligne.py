"""Operations enregistrees sans reseau: date reelle de l'operation et protection contre les doublons.

Le telephone garde l'operation en file d'attente, avec la date et la position du moment, puis l'envoie
des que la connexion revient. Chaque operation porte un identifiant fabrique par le telephone
(identifiantClient): si l'envoi est repete (reponse perdue, coupure), le serveur ne l'enregistre
qu'une seule fois et renvoie le meme resultat.
"""
import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import Evenement, TypeOperation, Utilisateur, maintenant

TOLERANCE_AVANCE = timedelta(minutes=5)   # horloge du telephone un peu en avance
ANCIENNETE_MAX = timedelta(days=30)       # au-dela, la date du telephone n'est pas crue
MOTIF_IDENTIFIANT = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def verifier_identifiant_client(identifiant: str | None) -> str | None:
    if identifiant is None or identifiant == "":
        return None
    if not MOTIF_IDENTIFIANT.match(identifiant):
        raise HTTPException(422, "Identifiant d'operation invalide (8 a 64 caracteres: lettres, chiffres, - et _).")
    return identifiant


def date_de_l_operation(date_telephone: datetime | None) -> datetime:
    """Date a enregistrer. Sans date du telephone, ou si elle est incoherente (dans le futur, trop
    ancienne), c'est l'heure du serveur: une horloge de telephone fausse ne doit pas faire perdre l'operation."""
    maintenant_serveur = maintenant()
    if date_telephone is None:
        return maintenant_serveur
    if date_telephone.tzinfo is not None:
        date_telephone = date_telephone.astimezone(timezone.utc).replace(tzinfo=None)
    if date_telephone > maintenant_serveur + TOLERANCE_AVANCE or date_telephone < maintenant_serveur - ANCIENNETE_MAX:
        return maintenant_serveur
    return date_telephone


def evenement_deja_enregistre(db: Session, utilisateur: Utilisateur, identifiant: str | None) -> Evenement | None:
    if identifiant is None:
        return None
    return db.query(Evenement).filter(Evenement.utilisateur_id == utilisateur.id,
                                      Evenement.identifiantClient == identifiant).first()
