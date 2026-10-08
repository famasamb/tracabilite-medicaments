"""Correction d'un test fragile de la lecture (suite de l'etape 54).

A lancer depuis la racine du projet:
    python installer_test_lecture.py

Le test de la route tirait un numero de serie au hasard, puis cherchait un flou qui convienne a ce numero. Pour
certains numeros, aucun flou ne convient, et le test echouait de temps en temps. Le test simule maintenant
l'echec de la lecture classique et garde l'image nette: il ne depend plus du numero tire.
Ce fichier peut ensuite etre supprime.
"""
import base64
import io
import zipfile
from pathlib import Path

ARCHIVE = """
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
AAEAAQBDAAAAKwYAAAAA
"""

if not Path("tests").is_dir():
    raise SystemExit("Lancez ce script depuis la racine du projet (le dossier qui contient le dossier tests).")

with zipfile.ZipFile(io.BytesIO(base64.b64decode("".join(ARCHIVE.split())))) as z:
    for nom in z.namelist():
        Path(nom).write_bytes(z.read(nom))
        print("ecrit:", nom)
print("Termine. Relancez pytest -q.")