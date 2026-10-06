"""Cas d'utilisation S'inscrire (fiche 2)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from .models import Role, Structure, TypeStructure, Utilisateur
from .references import trouver_reference
from .schemas import InscriptionEntree, InscriptionSortie
from .securite import hacher_mot_de_passe

router = APIRouter(prefix="/structures", tags=["Inscription"])


@router.post("/inscription", response_model=InscriptionSortie, status_code=201)
def s_inscrire(donnees: InscriptionEntree, db: Session = Depends(get_db)):
    """Inscrit une structure et cree le compte de son responsable."""
    s, r = donnees.structure, donnees.responsable
    reference = s.referenceAutorisation.strip()

    if s.type == TypeStructure.SR:
        raise HTTPException(403, "Un SR ne s'inscrit pas lui-meme: son compte responsable "
                                 "est cree par la PNA.")

    # Etape 3 de la fiche: recherche dans la base de reference
    if trouver_reference(db, reference, s.type) is None:
        raise HTTPException(422, "Aucune correspondance pour cette reference. Verifiez la "
                                 "reference saisie ou contactez l'ARP.")  # variante 3c

    if db.query(Structure).filter_by(referenceAutorisation=reference).first():
        raise HTTPException(409, "Une structure est deja inscrite avec cette reference.")  # variante 3b

    if db.query(Utilisateur).filter_by(identifiantConnexion=r.identifiantConnexion).first():
        raise HTTPException(409, "Cet identifiant de connexion est deja utilise.")

    # Etapes 4 et 5: enregistrement de la structure et creation du compte responsable
    structure = Structure(nom=s.nom, type=s.type, localisation=s.localisation,
                          referenceAutorisation=reference)
    responsable = Utilisateur(nom=r.nom, fonction=r.fonction,
                              identifiantConnexion=r.identifiantConnexion,
                              motDePasse=hacher_mot_de_passe(r.motDePasse),
                              role=Role.responsable, structure=structure)
    db.add_all([structure, responsable])
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Inscription impossible: reference ou identifiant deja utilises.")

    return InscriptionSortie(structure_id=structure.id, utilisateur_id=responsable.id,
                             message="Inscription enregistree. Vous pouvez vous connecter.")