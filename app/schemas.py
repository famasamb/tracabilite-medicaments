"""Formes des donnees echangees avec l'API (ce que l'application envoie et recoit)."""
from pydantic import BaseModel, Field

from .models import Role, TypeStructure


class StructureEntree(BaseModel):
    nom: str = Field(min_length=2, max_length=200)
    type: TypeStructure
    localisation: str = Field(min_length=2, max_length=200)
    referenceAutorisation: str = Field(min_length=1, max_length=100)


class ResponsableEntree(BaseModel):
    nom: str = Field(min_length=2, max_length=200)
    fonction: str = Field(min_length=2, max_length=100)
    identifiantConnexion: str = Field(min_length=3, max_length=100)
    motDePasse: str = Field(min_length=8, max_length=128)


class InscriptionEntree(BaseModel):
    structure: StructureEntree
    responsable: ResponsableEntree


class InscriptionSortie(BaseModel):
    structure_id: str
    utilisateur_id: str
    message: str
    
    
class JetonSortie(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfilSortie(BaseModel):
    id: str
    nom: str
    fonction: str
    role: Role
    structure_id: str
    structure_nom: str
    structure_type: TypeStructure