"""Agregation: regrouper des boites en cartons, et des cartons en palettes (fiche de conception de l'agregation).

Un carton ou une palette porte un SSCC, l'identifiant GS1 d'un colis logistique: 18 chiffres, le dernier
etant une cle de controle (meme calcul que pour le GTIN). Dans la norme, le SSCC contient le prefixe GS1 de
l'entreprise; ici, comme pour les numeros de serie, il est genere par le systeme.
"""
import hashlib
import re
import secrets
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .codes import cle_de_controle_gtin
from .models import (Anomalie, Conteneur, Contenu, EtatConteneur, Evenement, NiveauConteneur, StatutUnite,
                     TypeAnomalie, TypeOperation, TypeStructure, Unite, Utilisateur, maintenant)
from .routes_evenements import creer_evenement, deja_expediee_en_attente

TAILLE_MAX = 500   # elements au maximum dans un carton ou sur une palette


def generer_sscc(deja_pris: set[str] | None = None) -> str:
    """SSCC de 18 chiffres: chiffre d'extension 0, 16 chiffres au hasard, cle de controle."""
    pris = deja_pris or set()
    while True:
        corps = "0" + "".join(secrets.choice("0123456789") for _ in range(16))
        sscc = corps + str(cle_de_controle_gtin(corps))
        if sscc not in pris:
            return sscc


def sscc_valide(sscc: str) -> bool:
    return len(sscc) == 18 and sscc.isdigit() and cle_de_controle_gtin(sscc[:17]) == int(sscc[17])


def numeros_de_serie_contenus(db: Session, conteneur: Conteneur) -> list[str]:
    """Toutes les boites actuellement dans le conteneur (pour une palette: celles de ses cartons)."""
    series: list[str] = []
    for lien in (l for l in conteneur.contenu if l.dateRetrait is None):
        if lien.enfant_unite is not None:
            series.append(lien.enfant_unite)
        else:
            series.extend(numeros_de_serie_contenus(db, db.get(Conteneur, lien.enfant_conteneur)))
    return series


def _boites_avec_evenement(db: Session, series: list[str]) -> bool:
    """Vrai si l'une de ces boites a deja un evenement (elle est deja entree dans le circuit)."""
    for i in range(0, len(series), 500):
        if db.query(Evenement.id).filter(Evenement.numeroSerie.in_(series[i:i + 500])).first() is not None:
            return True
    return False


def composer(db: Session, utilisateur: Utilisateur, niveau: NiveauConteneur, elements: list[str]) -> Conteneur:
    """Cree un carton (a partir de numeros de serie) ou une palette (a partir de SSCC de cartons).

    Seul le fabricant compose, et seulement avec ses propres elements, encore dans son stock: aucune boite
    ne peut etre dans deux cartons, ni un carton sur deux palettes."""
    if not elements:
        raise HTTPException(422, "Indiquez au moins un element.")
    if len(elements) > TAILLE_MAX:
        raise HTTPException(422, f"{TAILLE_MAX} elements au maximum.")
    if len(set(elements)) != len(elements):
        raise HTTPException(422, "Un meme element est indique plusieurs fois.")

    structure = utilisateur.structure
    liens: list[Contenu] = []
    if niveau == NiveauConteneur.carton:
        for numero in elements:
            unite = db.get(Unite, numero)
            if unite is None:
                raise HTTPException(404, f"Identifiant inconnu: {numero}.")
            if unite.lot.produit.laboratoire != structure.nom:
                raise HTTPException(403, f"La boite {numero} n'a pas ete serialisee par votre structure.")
            if unite.statut != StatutUnite.active:
                raise HTTPException(409, f"La boite {numero} est deja desactivee.")
            if db.query(Contenu.id).filter(Contenu.enfant_unite == numero, Contenu.dateRetrait.is_(None)).first():
                raise HTTPException(409, f"La boite {numero} est deja dans un carton.")
            liens.append(Contenu(enfant_unite=numero))
        if _boites_avec_evenement(db, elements):
            raise HTTPException(409, "Une de ces boites est deja entree dans le circuit: elle ne peut plus changer de carton.")
    else:
        for sscc in elements:
            carton = db.get(Conteneur, sscc)
            if carton is None or carton.niveau != NiveauConteneur.carton:
                raise HTTPException(404, f"Carton inconnu: {sscc}.")
            if carton.structure_id != structure.id:
                raise HTTPException(403, f"Le carton {sscc} n'appartient pas a votre structure.")
            if carton.etat != EtatConteneur.actif:
                raise HTTPException(409, f"Le carton {sscc} a ete ouvert.")
            if db.query(Contenu.id).filter(Contenu.enfant_conteneur == sscc, Contenu.dateRetrait.is_(None)).first():
                raise HTTPException(409, f"Le carton {sscc} est deja sur une palette.")
            if _boites_avec_evenement(db, numeros_de_serie_contenus(db, carton)):
                raise HTTPException(409, f"Le carton {sscc} est deja entre dans le circuit.")
            liens.append(Contenu(enfant_conteneur=sscc))

    pris = {s for (s,) in db.query(Conteneur.sscc)}
    conteneur = Conteneur(sscc=generer_sscc(pris), niveau=niveau, etat=EtatConteneur.actif, structure_id=structure.id)
    conteneur.contenu = liens
    db.add(conteneur)
    db.commit()
    db.refresh(conteneur)
    return conteneur


# ---------- Etape 2: scanner un carton ou une palette (reception, expedition) ----------

def extraire_sscc(texte: str) -> str | None:
    """Dans le texte d'un code GS1, ex. (00)012345678901234567, renvoie le SSCC (18 chiffres)."""
    trouve = re.search(r"\(00\)(\d{18})", texte)
    return trouve.group(1) if trouve else None


def _prefixe_client(identifiant_client: str) -> str:
    """Identifiant de depart pour les evenements des boites d'un meme scan: court, stable, sans collision."""
    return hashlib.sha1(identifiant_client.encode()).hexdigest()[:20]


def conteneurs_a_mettre_a_jour(db: Session, conteneur: Conteneur) -> list[Conteneur]:
    """Le conteneur et, pour une palette, ses cartons: tous changent de detenteur a la reception."""
    liste = [conteneur]
    for lien in (l for l in conteneur.contenu if l.dateRetrait is None and l.enfant_conteneur):
        liste.append(db.get(Conteneur, lien.enfant_conteneur))
    return liste


def enregistrer_pour_conteneur(db: Session, utilisateur: Utilisateur, conteneur: Conteneur,
                               type_operation: TypeOperation, latitude: float | None, longitude: float | None,
                               date_heure: datetime | None, identifiant_client: str | None) -> tuple[int, int, bool, datetime]:
    """Un scan du carton (ou de la palette) cree l'evenement de chaque boite qu'il contient.

    Les regles sont celles d'une boite scannee seule: alerte si l'identifiant est deja desactive, ou si la
    reception n'a eu aucune expedition d'une autre structure avant. Renvoie (nombre de boites, nombre
    d'alertes, deja_enregistre, date de l'operation). Un envoi repete avec le meme identifiantClient ne cree rien de plus."""
    if conteneur.etat != EtatConteneur.actif:
        raise HTTPException(409, "Ce carton a ete ouvert: scannez ses boites une par une.")
    series = numeros_de_serie_contenus(db, conteneur)
    if not series:
        raise HTTPException(409, "Ce conteneur est vide.")

    prefixe = _prefixe_client(identifiant_client) if identifiant_client else None
    if prefixe is not None:
        deja = db.query(Evenement).filter(Evenement.utilisateur_id == utilisateur.id,
                                          Evenement.identifiantClient.like(prefixe + "-%")).all()
        if deja:
            alertes = sum(1 for e in deja if e.anomalies)
            return len(deja), alertes, True, min(e.dateHeure for e in deja)

    if db.query(Contenu.id).filter(Contenu.enfant_conteneur == conteneur.sscc, Contenu.dateRetrait.is_(None)).first():
        raise HTTPException(409, "Ce carton est sur une palette: scannez la palette, ou ouvrez-la d'abord.")

    if type_operation == TypeOperation.expedition:
        if conteneur.structure_id != utilisateur.structure_id:
            raise HTTPException(403, "Ce conteneur n'est pas chez vous: seule la structure qui le detient peut l'expedier.")
        if any(deja_expediee_en_attente(db, numero) for numero in series):
            raise HTTPException(409, "Ce conteneur a deja ete expedie et n'a pas encore ete recu: "
                                     "il ne peut pas etre expedie de nouveau.")

    alertes = 0
    date_operation = None
    for numero in series:
        unite = db.get(Unite, numero)
        evenement, anomalie, _ = creer_evenement(db, utilisateur, unite, type_operation, latitude, longitude,
                                         date_heure, f"{prefixe}-{numero}" if prefixe else None,
                                         par_conteneur=True)
        alertes += anomalie is not None
        date_operation = date_operation or evenement.dateHeure
    if type_operation == TypeOperation.reception:
        for c in conteneurs_a_mettre_a_jour(db, conteneur):
            c.structure_id = utilisateur.structure_id
    db.commit()
    return len(series), alertes, False, date_operation


# ---------- Etape 3: ouvrir un carton ou une palette (desagregation) ----------

def ouvrir(db: Session, utilisateur: Utilisateur, conteneur: Conteneur,
           presentes: list[str] | None) -> tuple[list[str], list[str], int]:
    """Declare qu'on sort le contenu d'un carton (ou les cartons d'une palette).

    Le conteneur passe a l'etat "desagrege" et son contenu redevient des elements seuls: l'historique est
    gardee (date de retrait). `presentes` est la liste de ce qu'on a vraiment trouve a l'ouverture; ce qui
    manque est signale par une alerte "carton incomplet" pour chaque boite concernee. Sans liste, on
    considere que tout est la. Renvoie (elements liberes, manquants, nombre d'alertes)."""
    if utilisateur.structure.type not in (TypeStructure.fabricant, TypeStructure.grossisteRepartiteur,
                                          TypeStructure.SR, TypeStructure.officine):
        raise HTTPException(403, "Votre structure n'est pas autorisee a ouvrir un conteneur.")
    if conteneur.etat != EtatConteneur.actif:
        raise HTTPException(409, "Ce conteneur est deja ouvert.")
    if conteneur.structure_id != utilisateur.structure_id:
        raise HTTPException(403, "Ce conteneur n'est pas chez vous: seule la structure qui le detient peut l'ouvrir.")
    if db.query(Contenu.id).filter(Contenu.enfant_conteneur == conteneur.sscc, Contenu.dateRetrait.is_(None)).first():
        raise HTTPException(409, "Ce carton est sur une palette: ouvrez d'abord la palette.")

    liens = [l for l in conteneur.contenu if l.dateRetrait is None]
    elements = [l.enfant_unite or l.enfant_conteneur for l in liens]
    manquants: list[str] = []
    if presentes is not None:
        if len(set(presentes)) != len(presentes):
            raise HTTPException(422, "Un meme element est indique plusieurs fois.")
        inconnus = [e for e in presentes if e not in elements]
        if inconnus:
            raise HTTPException(422, f"Cet element n'est pas dans ce conteneur: {inconnus[0]}.")
        manquants = [e for e in elements if e not in presentes]

    alertes = 0
    for element in manquants:
        if conteneur.niveau == NiveauConteneur.carton:
            series = [element]
        else:   # palette: un carton manquant, ce sont toutes ses boites qui sont a verifier
            series = numeros_de_serie_contenus(db, db.get(Conteneur, element))
        for numero in series:
            dernier = (db.query(Evenement).filter(Evenement.numeroSerie == numero)
                       .order_by(Evenement.dateHeure.desc()).first())
            if dernier is not None:   # l'alerte s'accroche au dernier evenement connu de la boite
                db.add(Anomalie(typeAnomalie=TypeAnomalie.cartonIncomplet, score=1.0, evenement=dernier))
                alertes += 1
    maintenant_ = maintenant()
    for lien in liens:
        lien.dateRetrait = maintenant_
    conteneur.etat = EtatConteneur.desagrege
    db.commit()
    return elements, manquants, alertes
