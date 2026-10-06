import enum
import uuid
from sqlalchemy import String, Enum, ForeignKey
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