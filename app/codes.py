"""Numeros de serie et codes 2D (DataMatrix GS1) pour la serialisation d'un lot."""
import re
import secrets
from datetime import date

import cv2
import numpy as np
import zxingcpp

# Alphabet sans caracteres ambigus (pas de 0/O, 1/I/L): plus facile a lire a la main
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LONGUEUR_SERIE = 12  # GS1 autorise jusqu'a 20 caracteres pour le numero de serie


def generer_numeros_serie(quantite: int, deja_pris: set[str] | None = None) -> list[str]:
    """Genere `quantite` numeros de serie uniques et imprevisibles.

    `deja_pris` contient les numeros deja utilises dans la base: on ne les reprend jamais.
    """
    if quantite <= 0:
        raise ValueError("la quantite doit etre superieure a zero")
    pris = set(deja_pris or ())
    nouveaux: list[str] = []
    while len(nouveaux) < quantite:
        serie = "".join(secrets.choice(ALPHABET) for _ in range(LONGUEUR_SERIE))
        if serie not in pris:
            pris.add(serie)
            nouveaux.append(serie)
    return nouveaux


def cle_de_controle_gtin(corps: str) -> int:
    """Chiffre de controle GS1 (modulo 10) pour les 13 premiers chiffres d'un GTIN-14."""
    somme = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(corps))
    return (10 - somme % 10) % 10


def gtin_valide(gtin: str) -> bool:
    """Vrai si le GTIN-14 est bien forme et si son chiffre de controle est correct."""
    return len(gtin) == 14 and gtin.isdigit() and cle_de_controle_gtin(gtin[:13]) == int(gtin[13])


def construire_contenu(gtin: str | None, id_produit: str, numero_lot: str,
                       date_peremption: date, numero_serie: str) -> str:
    """Contenu du code 2D, ecrit avec les identifiants d'application GS1.

    (01) GTIN, (17) peremption AAMMJJ, (10) lot, (21) numero de serie.
    Sans GTIN, on utilise (91) pour porter l'identifiant interne du produit.
    """
    if not 1 <= len(numero_lot) <= 20 or "(" in numero_lot or ")" in numero_lot:
        raise ValueError("numero de lot invalide (1 a 20 caracteres, sans parentheses)")
    if not 1 <= len(numero_serie) <= 20:
        raise ValueError("numero de serie invalide (1 a 20 caracteres)")
    peremption = date_peremption.strftime("%y%m%d")
    if gtin:
        if not gtin_valide(gtin):
            raise ValueError("GTIN invalide")
        return f"(01){gtin}(17){peremption}(10){numero_lot}(21){numero_serie}"
    return f"(17){peremption}(10){numero_lot}(21){numero_serie}(91){id_produit}"


def _lignes_lisibles(contenu: str) -> list[str]:
    """Texte lisible sous le code (norme GS1): une ligne par identifiant d'application, ex. (21)ABC123."""
    return [f"({ai}){valeur}" for ai, valeur in re.findall(r"\((\d{2,4})\)([^(]*)", contenu)]


def _ajouter_texte(image: np.ndarray, lignes: list[str]) -> np.ndarray:
    """Ajoute, sous le code, une marge blanche portant les lignes de texte lisible par une personne."""
    police, epaisseur = cv2.FONT_HERSHEY_SIMPLEX, 2
    largeur = image.shape[1]
    echelle = 1.0
    while echelle > 0.4 and max(cv2.getTextSize(t, police, echelle, epaisseur)[0][0] for t in lignes) > largeur - 24:
        echelle -= 0.05
    hauteur_ligne = int(cv2.getTextSize("Ag", police, echelle, epaisseur)[0][1] * 1.9)
    marge = np.full((hauteur_ligne * len(lignes) + 16, largeur), 255, dtype=np.uint8)
    for i, texte in enumerate(lignes):
        cv2.putText(marge, texte, (12, 8 + hauteur_ligne * (i + 1) - hauteur_ligne // 4), police, echelle, 0, epaisseur, cv2.LINE_AA)
    return np.vstack([image, marge])


def generer_image_code(contenu: str, echelle: int = 8, avec_texte: bool = False) -> bytes:
    """Fabrique l'image PNG d'un code DataMatrix GS1 a imprimer sur la boite.

    Avec avec_texte=True, le contenu est aussi ecrit en clair sous le code, comme sur une vraie etiquette:
    c'est ce que lit une personne quand elle doit saisir le numero de serie a la main."""
    code = zxingcpp.create_barcode(contenu, zxingcpp.BarcodeFormat.DataMatrix, gs1=True)
    image = np.array(code.to_image(scale=echelle))
    if avec_texte:
        if image.ndim == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image = _ajouter_texte(image, _lignes_lisibles(contenu))
    ok, png = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("impossible de fabriquer l'image du code")
    return png.tobytes()


def lire_code(image_png: bytes) -> str | None:
    """Relit un code 2D a partir d'une image; renvoie son contenu, ou None si illisible."""
    tableau = np.frombuffer(image_png, dtype=np.uint8)
    image = cv2.imdecode(tableau, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return None
    resultats = zxingcpp.read_barcodes(image)
    return resultats[0].text if resultats else None
