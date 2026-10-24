# Architecture de l'application

L'application est découpée en couches. Une couche ne dépend que de celles qui sont sous elle ; le test
`tests/test_architecture.py` le vérifie à chaque `pytest`.

```
 mobile (app/static/mobile)    sig/ (tableau de bord PNA)
              │  HTTP                 │  HTTP
              ▼                       ▼
        app/api        routes HTTP, schémas d'entrée et de sortie, droits d'accès
              │
              ▼
     app/services      règles métier : agrégation, hors-ligne, courriel, codes GS1, références
              │                         app/ia   lecture d'images (YOLO), moteur d'anomalies, alertes
              ▼                              │
     app/domaine       modèles (tables) ◄────┘
              │
              ▼
        app/core       base de données, sécurité, authentification, migration
```

| Dossier | Rôle | Contient |
|---|---|---|
| `app/api/` | Reçoit les requêtes et renvoie les réponses | une route par cas d'utilisation, `schemas.py` |
| `app/services/` | Règles métier, sans connaître HTTP | `agregation`, `horsligne`, `contenant`, `courriel`, `codes`, `references`, `sr` |
| `app/ia/` | Intelligence artificielle | `lecture` (YOLOv8), `anomalies` (moteur), `alertes`, `geo` |
| `app/domaine/` | Les objets du domaine | `models.py` |
| `app/core/` | Fondations techniques | `db`, `securite`, `auth`, `migration` |
| `sig/` | Application de la PNA (Streamlit) | carte et alertes |
| `jeu_de_donnees/` | Recherche : jeux de données, entraînement, évaluation | scripts et résultats |
| `tests/` | Tests automatiques | un fichier par fonctionnalité |

## Règles

1. Une route ne contient pas de règle métier : elle lit la requête, appelle un service, renvoie la réponse.
2. `domaine` ne dépend que de `core.db`. `core` ne dépend ni de `api`, ni de `services`, ni de `ia`.
3. `services` et `ia` ne dépendent jamais de `api`.

## Erreurs

Un service qui refuse une opération lève `ErreurMetier(statut, message)` (`app/services/erreurs.py`). Il ne connaît
pas HTTP : `app/main.py` traduit l'erreur en réponse JSON `{"detail": message}`. Le test d'architecture interdit
à `services` d'importer `fastapi`.

## Où est la règle ?

| Cas d'utilisation | Route (api) | Règles (services) |
|---|---|---|
| Réception, expédition d'une boîte | `api/evenements.py` | `services/evenements.py` |
| Dispensation | `api/dispensations.py` | `services/dispensations.py` |
| Carton, palette (composer, scanner, ouvrir) | `api/conteneurs.py` | `services/agregation.py` |
| Opérations faites sans réseau | (toutes) | `services/horsligne.py` |

## Lancer

- API : `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Moteur d'anomalies : `python -m app.ia.anomalies`
- Chargement des références : `python -m app.services.charger_references data/references_essai.csv`
- SIG : `python -m streamlit run sig/app.py`
