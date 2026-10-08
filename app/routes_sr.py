"""Cas d'utilisation Creer compte pharmacien chef de SR (fiche 4), reserve a la PNA."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import responsable_courant
from .db import get_db
from .models import Role, Structure, TypeStructure, Utilisateur
from .schemas import EmployeSortie, ResponsableEntree, SRSortie
from .securite import hacher_mot_de_passe

router = APIRouter(prefix="/sr", tags=["Services regionaux"])


def pna_courante(responsable: Utilisateur = Depends(responsable_courant)) -> Utilisateur:
    """Reserve au responsable d'une PNA."""
    if responsable.structure.type != TypeStructure.PNA:
        raise HTTPException(403, "Action reservee a la PNA.")
    return responsable


def _a_un_responsable(db: Session, sr_id: str) -> bool:
    return db.query(Utilisateur).filter_by(structure_id=sr_id, role=Role.responsable).first() is not None


@router.get("", response_model=list[SRSortie])
def lister_les_sr(pna: Utilisateur = Depends(pna_courante), db: Session = Depends(get_db)):
    """Etapes 1 et 2: la PNA voit ses SR et ceux qui ont deja un compte responsable."""
    sr = db.query(Structure).filter_by(mere_id=pna.structure_id, type=TypeStructure.SR) \
        .order_by(Structure.nom).all()
    return [SRSortie(id=s.id, nom=s.nom, localisation=s.localisation,
                     aUnResponsable=_a_un_responsable(db, s.id)) for s in sr]


@router.post("/{sr_id}/responsable", response_model=EmployeSortie, status_code=201)
def creer_responsable_sr(sr_id: str, donnees: ResponsableEntree,
                         pna: Utilisateur = Depends(pna_courante), db: Session = Depends(get_db)):
    """Etapes 3 a 6: cree le compte du pharmacien chef d'un SR de cette PNA."""
    sr = db.get(Structure, sr_id)
    if sr is None or sr.type != TypeStructure.SR or sr.mere_id != pna.structure_id:
        raise HTTPException(404, "SR introuvable parmi les services regionaux de votre PNA.")
    if _a_un_responsable(db, sr.id):  # variante 4c
        raise HTTPException(409, "Ce SR dispose deja d'un compte responsable.")
    if db.query(Utilisateur).filter_by(identifiantConnexion=donnees.identifiantConnexion).first():
        raise HTTPException(409, "Cet identifiant de connexion est deja utilise.")  # variante 4b
    if db.query(Utilisateur).filter_by(email=donnees.email).first():
        raise HTTPException(409, "Cette adresse e-mail est deja utilisee.")

    chef = Utilisateur(nom=donnees.nom, fonction=donnees.fonction,
                       identifiantConnexion=donnees.identifiantConnexion, email=donnees.email,
                       motDePasse=hacher_mot_de_passe(donnees.motDePasse),
                       role=Role.responsable, structure_id=sr.id)
    db.add(chef)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Compte impossible: identifiant ou adresse e-mail deja utilises, ou SR deja pourvu.")
    return EmployeSortie(id=chef.id, nom=chef.nom, fonction=chef.fonction,
                         identifiantConnexion=chef.identifiantConnexion, structure_id=sr.id,
                         message="Compte du pharmacien chef cree. Transmettez-lui son identifiant "
                                 "et son mot de passe initial.")
