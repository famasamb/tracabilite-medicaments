"""Cas d'utilisation Creer un compte employe (fiche 3)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import responsable_courant
from .db import get_db
from .models import Role, Utilisateur
from .schemas import EmployeEntree, EmployeSortie
from .securite import hacher_mot_de_passe

router = APIRouter(prefix="/employes", tags=["Employes"])


@router.post("", response_model=EmployeSortie, status_code=201)
def creer_compte_employe(donnees: EmployeEntree,
                         responsable: Utilisateur = Depends(responsable_courant),
                         db: Session = Depends(get_db)):
    """Le responsable cree un compte employe, rattache a sa propre structure."""
    if db.query(Utilisateur).filter_by(identifiantConnexion=donnees.identifiantConnexion).first():
        raise HTTPException(409, "Cet identifiant de connexion est deja utilise.")
    if db.query(Utilisateur).filter_by(email=donnees.email).first():
        raise HTTPException(409, "Cette adresse e-mail est deja utilisee.")

    employe = Utilisateur(nom=donnees.nom, fonction=donnees.fonction,
                          identifiantConnexion=donnees.identifiantConnexion, email=donnees.email,
                          motDePasse=hacher_mot_de_passe(donnees.motDePasse),
                          role=Role.employe, structure_id=responsable.structure_id)
    db.add(employe)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Cet identifiant de connexion ou cette adresse e-mail est deja utilise.")

    return EmployeSortie(id=employe.id, nom=employe.nom, fonction=employe.fonction,
                         identifiantConnexion=employe.identifiantConnexion,
                         structure_id=employe.structure_id,
                         message="Compte employe cree. Transmettez-lui son identifiant "
                                 "et son mot de passe initial.")
