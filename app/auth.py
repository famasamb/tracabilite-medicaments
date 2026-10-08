"""Session de l'utilisateur: jeton de connexion et controle d'acces selon le role."""
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Role, TypeStructure, Utilisateur

# En production, definir la variable d'environnement CLE_SECRETE avec une longue valeur aleatoire
CLE_SECRETE = os.getenv("CLE_SECRETE", "cle-de-developpement-a-changer-en-production")
ALGORITHME = "HS256"
DUREE_SESSION = timedelta(hours=8)

schema_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/connexion")


def creer_jeton(utilisateur: Utilisateur, duree: timedelta = DUREE_SESSION) -> str:
    """Fabrique le jeton signe qui prouve que l'utilisateur est connecte."""
    contenu = {"sub": utilisateur.id, "role": utilisateur.role.value, "v": utilisateur.versionSession or 0,
               "exp": datetime.now(timezone.utc) + duree}
    return jwt.encode(contenu, CLE_SECRETE, algorithm=ALGORITHME)


def utilisateur_courant(jeton: str = Depends(schema_oauth2), db: Session = Depends(get_db)) -> Utilisateur:
    """Renvoie l'utilisateur connecte, ou refuse la requete (401) si le jeton est absent, faux ou expire."""
    erreur = HTTPException(401, "Session invalide ou expiree. Reconnectez-vous.",
                           headers={"WWW-Authenticate": "Bearer"})
    try:
        contenu = jwt.decode(jeton, CLE_SECRETE, algorithms=[ALGORITHME])
    except jwt.PyJWTError:
        raise erreur
    utilisateur = db.get(Utilisateur, contenu.get("sub"))
    if utilisateur is None or contenu.get("v", 0) != (utilisateur.versionSession or 0):
        raise erreur   # compte supprime, ou mot de passe change depuis l'ouverture de cette session
    return utilisateur


def responsable_courant(utilisateur: Utilisateur = Depends(utilisateur_courant)) -> Utilisateur:
    """Comme utilisateur_courant, mais reserve au role responsable (403 pour un employe)."""
    if utilisateur.role != Role.responsable:
        raise HTTPException(403, "Action reservee au responsable de la structure.")
    return utilisateur


def fabricant_courant(utilisateur: Utilisateur = Depends(utilisateur_courant)) -> Utilisateur:
    """Comme utilisateur_courant, mais reserve aux utilisateurs d'une structure de type fabricant."""
    if utilisateur.structure.type != TypeStructure.fabricant:
        raise HTTPException(403, "Action reservee aux fabricants.")
    return utilisateur
