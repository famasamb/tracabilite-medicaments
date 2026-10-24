"""Corrige une ligne cassee de jeu_de_donnees/generer_historique.py (compte chef de SR). A lancer depuis la racine."""
from pathlib import Path

p = Path("jeu_de_donnees/generer_historique.py")
t = p.read_text(encoding="utf-8")
ancien = '"identifiantConnexion": f"sr.{ville.lower(), "email": f"sr.{ville.lower() + "@essai.sn"}", "motDePasse": MOT_DE_PASSE})'
nouveau = '"identifiantConnexion": f"sr.{ville.lower()}", "email": f"sr.{ville.lower()}@essai.sn", "motDePasse": MOT_DE_PASSE})'
if nouveau in t:
    print("Deja corrige.")
elif ancien in t:
    p.write_text(t.replace(ancien, nouveau, 1), encoding="utf-8")
    print("Corrige. Verifiez avec: python -m py_compile jeu_de_donnees/generer_historique.py")
else:
    raise SystemExit("Ligne attendue introuvable: envoyez-moi les lignes 80 a 86 du fichier.")
