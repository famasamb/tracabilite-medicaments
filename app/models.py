import enum
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, Enum, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def new_id() -> str:
    """Genere un identifiant unique pour chaque nouvelle ligne."""
    return uuid.uuid4().hex


def maintenant() -> datetime:
    """Date et heure actuelles (UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------- Enumerations (valeurs fixes de ton diagramme) ----------

class TypeStructure(str, enum.Enum):
    fabricant = "fabricant"
    grossisteRepartiteur = "grossisteRepartiteur"
    SR = "SR"
    officine = "officine"
    PNA = "PNA"


class Role(str, enum.Enum):
    responsable = "responsable"
    employe = "employe"


class StatutUnite(str, enum.Enum):
    active = "active"
    desactivee = "desactivee"


class TypeOperation(str, enum.Enum):
    reception = "reception"
    expedition = "expedition"
    dispensation = "dispensation"


class TypeAnomalie(str, enum.Enum):
    reutilisationIdentifiant = "reutilisationIdentifiant"
    ruptureSequence = "ruptureSequence"
    trajetInhabituel = "trajetInhabituel"
    concentrationInhabituelle = "concentrationInhabituelle"


# ---------- Classes ----------

class Structure(Base):
    __tablename__ = "structures"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    nom: Mapped[str] = mapped_column(String(200))
    type: Mapped[TypeStructure] = mapped_column(Enum(TypeStructure))
    localisation: Mapped[str] = mapped_column(String(200))
    referenceAutorisation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Association reflexive "rattacher a" : mere 0..1 / filiales 0..*
    mere_id: Mapped[str | None] = mapped_column(ForeignKey("structures.id"), nullable=True)
    mere: Mapped["Structure | None"] = relationship(remote_side=[id], back_populates="filiales")
    filiales: Mapped[list["Structure"]] = relationship(back_populates="mere")

    # Association "employer" : une structure emploie plusieurs utilisateurs
    utilisateurs: Mapped[list["Utilisateur"]] = relationship(back_populates="structure")


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    nom: Mapped[str] = mapped_column(String(200))
    fonction: Mapped[str] = mapped_column(String(100))
    identifiantConnexion: Mapped[str] = mapped_column(String(100), unique=True)
    motDePasse: Mapped[str] = mapped_column(String(300))  # on stockera un hash, jamais le mot de passe en clair
    role: Mapped[Role] = mapped_column(Enum(Role))

    # Association "employer" : un utilisateur appartient a une seule structure
    structure_id: Mapped[str] = mapped_column(ForeignKey("structures.id"))
    structure: Mapped[Structure] = relationship(back_populates="utilisateurs")

    # Association "enregistrer" : un utilisateur enregistre plusieurs evenements
    evenements: Mapped[list["Evenement"]] = relationship(back_populates="utilisateur")

    __table_args__ = (
        # Regle du diagramme: un seul responsable par structure
        Index("uq_un_responsable_par_structure", "structure_id", unique=True,
              sqlite_where=text("role = 'responsable'"),
              postgresql_where=text("role = 'responsable'")),
    )


class Produit(Base):
    __tablename__ = "produits"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)  # identifiant interne
    gtin: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)  # facultatif
    nom: Mapped[str] = mapped_column(String(200))
    laboratoire: Mapped[str] = mapped_column(String(200))
    composition: Mapped[str] = mapped_column(String(500))
    formePharmaceutique: Mapped[str] = mapped_column(String(100))
    conditionnement: Mapped[str] = mapped_column(String(200))

    # Association "decliner en" : un produit a plusieurs lots
    lots: Mapped[list["Lot"]] = relationship(back_populates="produit")


class Lot(Base):
    __tablename__ = "lots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    numeroLot: Mapped[str] = mapped_column(String(50))
    datePeremption: Mapped[date] = mapped_column(Date)
    quantite: Mapped[int] = mapped_column(Integer)

    produit_id: Mapped[str] = mapped_column(ForeignKey("produits.id"))
    produit: Mapped[Produit] = relationship(back_populates="lots")

    # Composition "contenir" : les unites n'existent que dans leur lot
    unites: Mapped[list["Unite"]] = relationship(back_populates="lot", cascade="all, delete-orphan")

    __table_args__ = (
        # Un meme numero de lot ne peut pas etre enregistre deux fois pour un produit
        UniqueConstraint("produit_id", "numeroLot", name="uq_lot_par_produit"),
    )


class Unite(Base):
    __tablename__ = "unites"

    # Le numero de serie est la cle primaire: il est donc unique dans tout le systeme
    numeroSerie: Mapped[str] = mapped_column(String(40), primary_key=True)
    statut: Mapped[StatutUnite] = mapped_column(Enum(StatutUnite), default=StatutUnite.active)
    dateCreation: Mapped[datetime] = mapped_column(DateTime, default=maintenant)

    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), index=True)
    lot: Mapped[Lot] = relationship(back_populates="unites")

    # Association "avoir pour historique" : une unite a plusieurs evenements
    evenements: Mapped[list["Evenement"]] = relationship(
        back_populates="unite", order_by="Evenement.dateHeure")


class Evenement(Base):
    __tablename__ = "evenements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    typeOperation: Mapped[TypeOperation] = mapped_column(Enum(TypeOperation))
    dateHeure: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    synchronise: Mapped[bool] = mapped_column(Boolean, default=True)

    # Association "avoir pour historique" : un evenement concerne une seule unite
    numeroSerie: Mapped[str] = mapped_column(ForeignKey("unites.numeroSerie"), index=True)
    unite: Mapped[Unite] = relationship(back_populates="evenements")

    # Association "enregistrer" : un evenement est enregistre par un seul utilisateur
    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"))
    utilisateur: Mapped[Utilisateur] = relationship(back_populates="evenements")

    # Association "reveler" : un evenement peut reveler plusieurs anomalies
    anomalies: Mapped[list["Anomalie"]] = relationship(back_populates="evenement")


class Anomalie(Base):
    __tablename__ = "anomalies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    typeAnomalie: Mapped[TypeAnomalie] = mapped_column(Enum(TypeAnomalie))
    score: Mapped[float] = mapped_column(Float)
    dateDetection: Mapped[datetime] = mapped_column(DateTime, default=maintenant)
    statut: Mapped[str] = mapped_column(String(50), default="a_verifier")  # valeurs a definir plus tard

    evenement_id: Mapped[str] = mapped_column(ForeignKey("evenements.id"), index=True)
    evenement: Mapped[Evenement] = relationship(back_populates="anomalies")
    
    
class ReferenceAutorisation(Base):
    """Base de reference des autorisations officielles (donnees importees, pas une classe du domaine).

    Elle sert a verifier la reference saisie lors de l'inscription d'une structure.
    """
    __tablename__ = "references_autorisation"

    reference: Mapped[str] = mapped_column(String(100), primary_key=True)
    nom: Mapped[str] = mapped_column(String(200))
    type: Mapped[TypeStructure] = mapped_column(Enum(TypeStructure))