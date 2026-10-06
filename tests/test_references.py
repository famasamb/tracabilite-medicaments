"""Tests de la base de reference des autorisations."""
from app.models import ReferenceAutorisation, TypeStructure
from app.references import charger_references, trouver_reference


def ecrire_csv(tmp_path):
    fichier = tmp_path / "refs.csv"
    fichier.write_text("reference,nom,type\nREF-1,Labo A,fabricant\nREF-2,Pharmacie B,officine\n",
                       encoding="utf-8")
    return fichier


def test_import_du_fichier_csv(db, tmp_path):
    assert charger_references(db, ecrire_csv(tmp_path)) == 2
    assert db.query(ReferenceAutorisation).count() == 2


def test_reimporter_ne_duplique_pas(db, tmp_path):
    fichier = ecrire_csv(tmp_path)
    charger_references(db, fichier)
    assert charger_references(db, fichier) == 0
    assert db.query(ReferenceAutorisation).count() == 2


def test_reference_trouvee_si_le_type_correspond(db, tmp_path):
    charger_references(db, ecrire_csv(tmp_path))
    assert trouver_reference(db, "REF-1", TypeStructure.fabricant).nom == "Labo A"
    assert trouver_reference(db, " REF-1 ", TypeStructure.fabricant) is not None


def test_reference_inconnue_ou_de_mauvais_type(db, tmp_path):
    charger_references(db, ecrire_csv(tmp_path))
    assert trouver_reference(db, "REF-9", TypeStructure.fabricant) is None
    assert trouver_reference(db, "REF-1", TypeStructure.officine) is None


def test_le_fichier_de_test_du_projet_se_charge(db):
    assert charger_references(db, "data/references_test.csv") == 4