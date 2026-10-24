"""Lecture d'une image televersee par l'application mobile (limite de taille)."""
from fastapi import HTTPException, UploadFile

from app.services.evenements import TAILLE_MAX_IMAGE


async def lire_televersement(image: UploadFile | None) -> bytes | None:
    """Octets de l'image, ou None s'il n'y en a pas. Refuse (413) une image de plus de 5 Mo."""
    if image is None:
        return None
    contenu = await image.read(TAILLE_MAX_IMAGE + 1)
    if len(contenu) > TAILLE_MAX_IMAGE:
        raise HTTPException(413, "Image trop volumineuse (5 Mo maximum).")
    return contenu
