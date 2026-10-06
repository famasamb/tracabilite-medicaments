"""Cas d'utilisation S'authentifier (fiche 1)."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .auth import creer_jeton, utilisateur_courant
from .db import get_db
from .models import Utilisateur
from .schemas import JetonSortie, ProfilSortie
from .securite import verifier_mot_de_passe

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/connexion", response_model=JetonSortie)
def se_connecter(formulaire: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Ouvre une session. Le champ `username` est l'identifiant de connexion."""
    utilisateur = db.query(Utilisateur).filter_by(identifiantConnexion=formulaire.username).first()
    if utilisateur is None:                                            # variante 3c
        raise HTTPException(401, "Aucun compte ne correspond a cet identifiant. "
                                 "Contactez le responsable de votre structure.")
    if not verifier_mot_de_passe(formulaire.password, utilisateur.motDePasse):   # variante 3b
        raise HTTPException(401, "Identifiant ou mot de passe incorrect.")
    return JetonSortie(access_token=creer_jeton(utilisateur))


@router.get("/moi", response_model=ProfilSortie)
def mon_profil(utilisateur: Utilisateur = Depends(utilisateur_courant)):
    """Renvoie le profil de l'utilisateur connecte."""
    return ProfilSortie(id=utilisateur.id, nom=utilisateur.nom, fonction=utilisateur.fonction,
                        role=utilisateur.role, structure_id=utilisateur.structure_id,
                        structure_nom=utilisateur.structure.nom,
                        structure_type=utilisateur.structure.type)