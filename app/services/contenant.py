"""Savoir si une boite est encore dans un carton actif (aucune dependance vers les routes)."""
from sqlalchemy.orm import Session

from app.domaine.models import Conteneur, Contenu, EtatConteneur


def conteneur_actif_de_la_boite(db: Session, numero_serie: str) -> Conteneur | None:
    """Le carton actif qui contient cette boite en ce moment, ou None si elle est seule."""
    lien = (db.query(Contenu).filter(Contenu.enfant_unite == numero_serie, Contenu.dateRetrait.is_(None)).first())
    if lien is None:
        return None
    conteneur = db.get(Conteneur, lien.parent_sscc)
    return conteneur if conteneur is not None and conteneur.etat == EtatConteneur.actif else None
