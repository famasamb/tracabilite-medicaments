"""Cas d'utilisation Serialiser un lot (diagramme de sequence du meme nom)."""
import io
import zipfile
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import fabricant_courant
from .codes import construire_contenu, generer_image_code, generer_numeros_serie
from .db import get_db
from .models import Lot, Produit, StatutUnite, Unite, Utilisateur
from .schemas import LotEntree

router = APIRouter(prefix="/lots", tags=["Lots"])


def _numeros_libres(db: Session, quantite: int) -> list[str]:
    """Numeros de serie neufs: on verifie qu'aucun n'existe deja dans la base."""
    while True:
        candidats = generer_numeros_serie(quantite)
        pris = set()
        for i in range(0, len(candidats), 500):
            morceau = candidats[i:i + 500]
            pris.update(n for (n,) in db.query(Unite.numeroSerie).filter(Unite.numeroSerie.in_(morceau)))
        if not pris:
            return candidats
        # collision (tres improbable): on recommence avec de nouveaux numeros


@router.post("/serialisation", status_code=201, response_class=Response,
             responses={201: {"content": {"application/zip": {}}, "description": "Archive ZIP des codes 2D"}})
def serialiser_lot(donnees: LotEntree,
                   utilisateur: Utilisateur = Depends(fabricant_courant),
                   db: Session = Depends(get_db)):
    """Cree le lot et ses unites (statut active), puis renvoie un ZIP avec un code DataMatrix GS1 par unite."""
    produit = db.get(Produit, donnees.produit_id)
    if produit is None:
        raise HTTPException(404, "Produit introuvable. Enregistrez-le d'abord.")
    if produit.laboratoire != utilisateur.structure.nom:
        raise HTTPException(403, "Ce produit n'appartient pas a votre structure.")
    if donnees.datePeremption <= date.today():
        raise HTTPException(422, "La date de peremption doit etre dans le futur.")
    if db.query(Lot).filter_by(produit_id=produit.id, numeroLot=donnees.numeroLot).first():
        raise HTTPException(409, "Ce lot est deja serialise pour ce produit.")

    # Etape de serialisation: lot + unites, enregistres ensemble (tout ou rien)
    numeros = _numeros_libres(db, donnees.quantite)
    lot = Lot(numeroLot=donnees.numeroLot, datePeremption=donnees.datePeremption,
              quantite=donnees.quantite, produit=produit)
    lot.unites = [Unite(numeroSerie=n, statut=StatutUnite.active) for n in numeros]
    db.add(lot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ce lot est deja serialise pour ce produit.")

    # Fabrication des codes 2D a imprimer
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for n in numeros:
            contenu = construire_contenu(produit.gtin, produit.id, lot.numeroLot,
                                         lot.datePeremption, n)
            zf.writestr(f"{n}.png", generer_image_code(contenu))
    nom_fichier = f"codes_{lot.numeroLot}.zip"
    return Response(content=archive.getvalue(), media_type="application/zip", status_code=201,
                    headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"',
                             "X-Lot-Id": lot.id,
                             "X-Message": f"Lot {lot.numeroLot} serialise: {len(numeros)} codes generes."})