import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Adresse de la base. Par defaut: un fichier SQLite dans le dossier du projet.
# Pour PostgreSQL plus tard, on definira la variable DATABASE_URL, par exemple:
# postgresql+psycopg://utilisateur:motdepasse@localhost/tracabilite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tracabilite.db")

# SQLite demande cette option quand plusieurs fils d'execution l'utilisent
options = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Le "moteur" est l'objet qui parle a la base
engine = create_engine(DATABASE_URL, connect_args=options)

# Une "session" est une conversation avec la base (lire, ecrire, valider)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Classe mere de toutes nos classes (Structure, Produit, Lot...)."""
    pass


def get_db():
    """Ouvre une session pour une requete de l'API, puis la referme."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()