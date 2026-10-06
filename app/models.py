import enum
import uuid
from sqlalchemy import String, Enum, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def new_id() -> str:
    """Genere un identifiant unique pour chaque nouvelle ligne."""
    return uuid.uuid4().hex


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

    __table_args__ = (
        # Regle du diagramme: un seul responsable par structure
        Index("uq_un_responsable_par_structure", "structure_id", unique=True,
              sqlite_where=text("role = 'responsable'"),
              postgresql_where=text("role = 'responsable'")),
    )