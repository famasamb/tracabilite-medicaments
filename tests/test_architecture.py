"""Regles d'architecture: chaque couche ne depend que des couches du dessous (voir docs/ARCHITECTURE.md).

    domaine  ->  core.db seulement
    core     ->  jamais api, services, ia
    ia       ->  jamais api
    services ->  jamais api

Les services ne connaissent pas non plus HTTP: ils levent ErreurMetier (app/services/erreurs.py), que
l'application traduit en reponse. EXCEPTIONS liste les entorses tolerees (aucune pour l'instant).
"""
import ast
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent / "app"
INTERDITS = {
    "domaine": ("app.api", "app.services", "app.ia", "app.core.auth", "app.core.securite", "app.core.migration"),
    "core": ("app.api", "app.services", "app.ia"),
    "ia": ("app.api",),
    "services": ("app.api", "fastapi"),
}
EXCEPTIONS: set[tuple[str, str]] = set()


def imports_de(chemin: Path) -> set[str]:
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    trouves = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.ImportFrom) and noeud.module and noeud.module.startswith("app"):
            trouves.add(noeud.module)
        elif isinstance(noeud, ast.Import):
            trouves.update(a.name for a in noeud.names if a.name.startswith("app"))
    return trouves


def test_les_couches_respectent_le_sens_des_dependances():
    fautes = []
    for couche, interdits in INTERDITS.items():
        for fichier in (RACINE / couche).rglob("*.py"):
            relatif = fichier.relative_to(RACINE).as_posix()
            for module in imports_de(fichier):
                if any(module == i or module.startswith(i + ".") for i in interdits) and (relatif, module) not in EXCEPTIONS:
                    fautes.append(f"{relatif} importe {module}")
    assert not fautes, "Dependances interdites:\n" + "\n".join(sorted(fautes))


def test_chaque_couche_est_un_paquet():
    for couche in ("core", "domaine", "api", "services", "ia"):
        assert (RACINE / couche / "__init__.py").exists()
