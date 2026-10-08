"""Formes des donnees echangees avec l'API (ce que l'application envoie et recoit)."""
from datetime import date, datetime

from pydantic import BaseModel, Field

from .models import Role, StatutUnite, TypeAnomalie, TypeOperation, TypeStructure


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


class ChangementMotDePasse(BaseModel):
    motDePasseActuel: str = Field(min_length=1, max_length=128)
    nouveauMotDePasse: str = Field(min_length=8, max_length=128)


class EmployeEntree(BaseModel):
    nom: str = Field(min_length=2, max_length=200)
    fonction: str = Field(min_length=2, max_length=100)
    identifiantConnexion: str = Field(min_length=3, max_length=100)
    motDePasse: str = Field(min_length=8, max_length=128)


class EmployeSortie(BaseModel):
    id: str
    nom: str
    fonction: str
    identifiantConnexion: str
    structure_id: str
    message: str


class ProduitEntree(BaseModel):
    nom: str = Field(min_length=2, max_length=200)
    composition: str = Field(min_length=2, max_length=500)
    formePharmaceutique: str = Field(min_length=2, max_length=100)
    conditionnement: str = Field(min_length=2, max_length=200)
    gtin: str | None = Field(default=None, description="Facultatif: 14 chiffres, cle de controle valide")


class ProduitSortie(BaseModel):
    id: str
    gtin: str | None
    nom: str
    laboratoire: str
    composition: str
    formePharmaceutique: str
    conditionnement: str
    message: str


class LotEntree(BaseModel):
    produit_id: str = Field(min_length=1, max_length=32)
    numeroLot: str = Field(min_length=1, max_length=20, pattern=r"^[^()]+$")
    datePeremption: date
    quantite: int = Field(gt=0, le=10000, description="Nombre d'unites a serialiser (10 000 maximum par lot)")


class ProduitResume(BaseModel):
    id: str
    gtin: str | None
    nom: str
    laboratoire: str
    formePharmaceutique: str
    conditionnement: str


class EvenementSortie(BaseModel):
    id: str
    numeroSerie: str
    typeOperation: TypeOperation
    dateHeure: datetime
    latitude: float | None
    longitude: float | None
    alerte: bool
    message: str


class DernierEvenement(BaseModel):
    typeOperation: TypeOperation
    dateHeure: datetime
    latitude: float | None
    longitude: float | None


class AnomalieAssociee(BaseModel):
    typeAnomalie: TypeAnomalie
    statut: str
    dateDetection: datetime


class StatutUniteSortie(BaseModel):
    numeroSerie: str
    statut: StatutUnite
    dernierEvenement: DernierEvenement | None
    anomalie: AnomalieAssociee | None


class SRSortie(BaseModel):
    id: str
    nom: str
    localisation: str
    aUnResponsable: bool


class FiltreTableau(BaseModel):
    srId: str | None
    du: date | None
    au: date | None


class PointCarte(BaseModel):
    latitude: float
    longitude: float
    typeOperation: TypeOperation
    dateHeure: datetime
    sr: str


class AlerteRecente(BaseModel):
    typeAnomalie: TypeAnomalie
    statut: str
    dateDetection: datetime
    sr: str
    numeroSerie: str


class TableauDeBordSortie(BaseModel):
    avertissement: str
    filtre: FiltreTableau
    message: str | None
    nombreEvenements: int
    unitesSuivies: int
    anomaliesSignalees: int
    anomaliesParType: dict[str, int]
    pointsCarte: list[PointCarte]
    alertesRecentes: list[AlerteRecente]
