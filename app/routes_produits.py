"""Cas d'utilisation Enregistrer les informations d'un produit."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import fabricant_courant
from .codes import gtin_valide
from .db import get_db
from .models import Produit, Utilisateur
from .schemas import ProduitEntree, ProduitResume, ProduitSortie

router = APIRouter(prefix="/produits", tags=["Produits"])


@router.post("", response_model=ProduitSortie, status_code=201)
def enregistrer_produit(donnees: ProduitEntree,
                        utilisateur: Utilisateur = Depends(fabricant_courant),
                        db: Session = Depends(get_db)):
    """Un fabricant enregistre un produit. Le laboratoire est le nom de sa structure."""
    gtin = donnees.gtin.strip() if donnees.gtin else None
    if gtin:
        if not gtin_valide(gtin):
            raise HTTPException(422, "GTIN invalide: 14 chiffres avec une cle de controle correcte.")
        if db.query(Produit).filter_by(gtin=gtin).first():
            raise HTTPException(409, "Un produit est deja enregistre avec ce GTIN.")

    produit = Produit(gtin=gtin, nom=donnees.nom, laboratoire=utilisateur.structure.nom,
                      composition=donnees.composition,
                      formePharmaceutique=donnees.formePharmaceutique,
                      conditionnement=donnees.conditionnement)
    db.add(produit)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Un produit est deja enregistre avec ce GTIN.")

    return ProduitSortie(id=produit.id, gtin=produit.gtin, nom=produit.nom,
                         laboratoire=produit.laboratoire, composition=produit.composition,
                         formePharmaceutique=produit.formePharmaceutique,
                         conditionnement=produit.conditionnement,
                         message="Produit enregistre.")


@router.get("", response_model=list[ProduitResume])
def rechercher_produits(q: str = Query(min_length=2, max_length=100, description="Nom (ou debut du nom) ou GTIN"),
                        utilisateur: Utilisateur = Depends(fabricant_courant),
                        db: Session = Depends(get_db)):
    """Recherche, parmi les produits de son laboratoire, par nom ou par GTIN (etape 3 de la serialisation)."""
    motif = q.strip()
    requete = db.query(Produit).filter(Produit.laboratoire == utilisateur.structure.nom)
    requete = requete.filter(or_(Produit.nom.ilike(f"%{motif}%"), Produit.gtin == motif))
    return requete.order_by(Produit.nom).limit(50).all()