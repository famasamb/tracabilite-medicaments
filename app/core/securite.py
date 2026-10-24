"""Mots de passe: on ne stocke jamais le mot de passe, seulement son empreinte (hash)."""
import base64
import hashlib
import hmac
import secrets

# Parametres de scrypt (algorithme concu pour ralentir les attaques par force brute)
_N, _R, _P = 2**14, 8, 1
LONGUEUR_MINIMALE = 8


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Renvoie une empreinte du mot de passe, avec un sel aleatoire propre a chaque utilisateur."""
    if len(mot_de_passe) < LONGUEUR_MINIMALE:
        raise ValueError(f"le mot de passe doit contenir au moins {LONGUEUR_MINIMALE} caracteres")
    sel = secrets.token_bytes(16)
    empreinte = hashlib.scrypt(mot_de_passe.encode(), salt=sel, n=_N, r=_R, p=_P, dklen=32)
    return "scrypt${}${}${}${}${}".format(
        _N, _R, _P, base64.b64encode(sel).decode(), base64.b64encode(empreinte).decode())


def verifier_mot_de_passe(mot_de_passe: str, enregistre: str) -> bool:
    """Vrai si le mot de passe correspond a l'empreinte enregistree."""
    try:
        _, n, r, p, sel, attendu = enregistre.split("$")
        calcule = hashlib.scrypt(mot_de_passe.encode(), salt=base64.b64decode(sel),
                                 n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calcule, base64.b64decode(attendu))
    except (ValueError, TypeError):
        return False