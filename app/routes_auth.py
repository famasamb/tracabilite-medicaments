"""Cas d'utilisation S'authentifier (fiche 1), changement et recuperation du mot de passe."""
import hashlib
import secrets
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import courriel
from .auth import creer_jeton, utilisateur_courant
from .db import get_db
from .models import JetonReinitialisation, Utilisateur, maintenant
from .schemas import (ChangementCourriel, ChangementMotDePasse, DemandeReinitialisation, JetonSortie,
                      ProfilSortie, Reinitialisation)
from .securite import hacher_mot_de_passe, verifier_mot_de_passe

router = APIRouter(prefix="/auth", tags=["Authentification"])

DUREE_LIEN = timedelta(minutes=30)
DEMANDES_MAX_PAR_HEURE = 3
MESSAGE_DEMANDE = ("Si cette adresse correspond a un compte, un e-mail contenant un lien de "
                   "reinitialisation vient d'etre envoye. Le lien est valable 30 minutes.")


def _empreinte(jeton: str) -> str:
    return hashlib.sha256(jeton.encode()).hexdigest()


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
                        structure_type=utilisateur.structure.type, email=utilisateur.email)


def _prevenir_changement(utilisateur: Utilisateur, taches: BackgroundTasks) -> None:
    """Courriel d'alerte: si ce n'est pas l'utilisateur qui a change son mot de passe, il le saura."""
    if utilisateur.email:
        taches.add_task(courriel.envoyer, utilisateur.email, "Votre mot de passe a ete modifie",
                        f"Bonjour {utilisateur.nom},\n\nLe mot de passe de votre compte "
                        f"({utilisateur.identifiantConnexion}) vient d'etre modifie.\n\n"
                        "Si vous n'etes pas a l'origine de ce changement, utilisez tout de suite "
                        "\"Mot de passe oublie ?\" sur l'ecran de connexion, puis prevenez le "
                        "responsable de votre structure.\n")


@router.post("/mot-de-passe")
def changer_mot_de_passe(donnees: ChangementMotDePasse, taches: BackgroundTasks,
                         utilisateur: Utilisateur = Depends(utilisateur_courant),
                         db: Session = Depends(get_db)):
    """Chaque utilisateur change son propre mot de passe, en prouvant qu'il connait l'actuel.

    Les autres sessions ouvertes sont fermees; la session courante recoit un nouveau jeton.
    """
    if not verifier_mot_de_passe(donnees.motDePasseActuel, utilisateur.motDePasse):
        raise HTTPException(400, "Mot de passe actuel incorrect.")
    if donnees.nouveauMotDePasse == donnees.motDePasseActuel:
        raise HTTPException(422, "Le nouveau mot de passe doit etre different de l'actuel.")
    utilisateur.motDePasse = hacher_mot_de_passe(donnees.nouveauMotDePasse)
    utilisateur.versionSession = (utilisateur.versionSession or 0) + 1
    db.commit()
    _prevenir_changement(utilisateur, taches)
    return {"message": "Mot de passe modifie.", "access_token": creer_jeton(utilisateur), "token_type": "bearer"}


@router.put("/courriel")
def changer_courriel(donnees: ChangementCourriel, utilisateur: Utilisateur = Depends(utilisateur_courant),
                     db: Session = Depends(get_db)):
    """Enregistre ou modifie l'adresse e-mail du compte (mot de passe demande)."""
    if not verifier_mot_de_passe(donnees.motDePasseActuel, utilisateur.motDePasse):
        raise HTTPException(400, "Mot de passe actuel incorrect.")
    autre = db.query(Utilisateur).filter(Utilisateur.email == donnees.email, Utilisateur.id != utilisateur.id).first()
    if autre is not None:
        raise HTTPException(409, "Cette adresse e-mail est deja utilisee.")
    utilisateur.email = donnees.email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Cette adresse e-mail est deja utilisee.")
    return {"message": "Adresse e-mail enregistree.", "email": utilisateur.email}


@router.post("/mot-de-passe-oublie")
def mot_de_passe_oublie(donnees: DemandeReinitialisation, taches: BackgroundTasks, db: Session = Depends(get_db)):
    """Envoie un lien de reinitialisation a l'adresse du compte.

    La reponse est toujours la meme, que l'adresse existe ou non: on ne revele pas quels comptes existent.
    """
    maintenant_ = maintenant()
    db.query(JetonReinitialisation).filter(JetonReinitialisation.expireLe < maintenant_ - timedelta(days=1)).delete()
    utilisateur = db.query(Utilisateur).filter_by(email=donnees.email).first()
    if utilisateur is not None:
        recents = db.query(JetonReinitialisation).filter(
            JetonReinitialisation.utilisateur_id == utilisateur.id,
            JetonReinitialisation.creeLe > maintenant_ - timedelta(hours=1)).count()
        if recents < DEMANDES_MAX_PAR_HEURE:
            # Un seul lien valable a la fois: les precedents sont invalides
            for ancien in db.query(JetonReinitialisation).filter_by(utilisateur_id=utilisateur.id, utiliseLe=None):
                ancien.utiliseLe = maintenant_
            jeton = secrets.token_urlsafe(32)
            db.add(JetonReinitialisation(utilisateur_id=utilisateur.id, empreinte=_empreinte(jeton),
                                         expireLe=maintenant_ + DUREE_LIEN))
            db.commit()
            lien = f"{courriel.url_publique()}/mobile/#/reinitialiser/{jeton}"
            taches.add_task(courriel.envoyer, utilisateur.email, "Reinitialisation de votre mot de passe",
                            f"Bonjour {utilisateur.nom},\n\nVous avez demande a reinitialiser le mot de passe "
                            f"de votre compte ({utilisateur.identifiantConnexion}).\n\n"
                            f"Ouvrez ce lien pour choisir un nouveau mot de passe (valable 30 minutes, "
                            f"utilisable une seule fois) :\n{lien}\n\n"
                            "Si vous n'etes pas a l'origine de cette demande, ignorez ce message: "
                            "votre mot de passe actuel reste inchange.\n")
        else:
            db.commit()
    else:
        db.commit()
    return {"message": MESSAGE_DEMANDE}


@router.post("/reinitialiser-mot-de-passe")
def reinitialiser_mot_de_passe(donnees: Reinitialisation, taches: BackgroundTasks, db: Session = Depends(get_db)):
    """Choisit un nouveau mot de passe grace au lien recu par e-mail (une seule utilisation)."""
    maintenant_ = maintenant()
    jeton = db.query(JetonReinitialisation).filter_by(empreinte=_empreinte(donnees.jeton)).first()
    if jeton is None or jeton.utiliseLe is not None or jeton.expireLe < maintenant_:
        raise HTTPException(400, "Lien invalide ou expire. Refaites une demande.")
    utilisateur = db.get(Utilisateur, jeton.utilisateur_id)
    utilisateur.motDePasse = hacher_mot_de_passe(donnees.nouveauMotDePasse)
    utilisateur.versionSession = (utilisateur.versionSession or 0) + 1   # ferme toutes les sessions ouvertes
    for t in db.query(JetonReinitialisation).filter_by(utilisateur_id=utilisateur.id, utiliseLe=None):
        t.utiliseLe = maintenant_
    db.commit()
    _prevenir_changement(utilisateur, taches)
    return {"message": "Mot de passe modifie. Vous pouvez vous connecter."}
