# Traçabilité des médicaments

Système intelligent de reconnaissance et de traçabilité des produits par code-barres et intelligence artificielle
(projet de fin d'études, M2 IABD, ESP / UCAD, Dakar). Chaque boîte porte un code DataMatrix GS1 ; chaque
mouvement (expédition, réception, dispensation) est enregistré, et des règles et un moteur d'anomalies
signalent les situations à faire vérifier.

## Ce que fait l'application

- **Sérialisation** : le fabricant enregistre un produit et un lot, et génère un code DataMatrix par boîte.
- **Agrégation** : le fabricant regroupe des boîtes en cartons et des cartons en palettes (SSCC, étiquette imprimable).
- **Circuit** : expédition, réception et dispensation par scan d'une boîte, d'un carton ou d'une palette,
  avec ou sans réseau (les opérations sont gardées sur le téléphone puis envoyées).
- **Lecture d'images** : lecture classique du code, puis YOLOv8 en secours quand le code est abîmé.
- **Anomalies** : réutilisation d'identifiant, rupture de séquence, boîte hors carton, carton incomplet
  (à l'enregistrement) ; trajet inhabituel et concentration inhabituelle (moteur d'analyse).
- **Tableau de bord PNA** (`sig/`) : carte et alertes du circuit public.

## Structure

Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour le détail des couches.

```
app/
  api/        routes HTTP et schémas
  services/   règles métier
  ia/         lecture YOLO, moteur d'anomalies, alertes
  domaine/    modèles
  core/       base de données, sécurité, authentification
  static/mobile/   application mobile (PWA)
sig/              tableau de bord de la PNA (Streamlit)
jeu_de_donnees/   jeux de données, entraînement et évaluation
outils/           scripts d'essai
tests/            tests automatiques
docs/             documentation
```

## Installation

```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env           # puis remplir les valeurs (le fichier .env ne va jamais sur Git)
```

## Lancer

```
uvicorn app.main:app --host 0.0.0.0 --port 8000      # API et application mobile (/mobile)
python -m streamlit run sig/app.py                   # tableau de bord PNA (l'API doit tourner)
python -m app.ia.anomalies                           # moteur d'anomalies sur tout l'historique
python -m app.services.charger_references data/references_essai.csv   # références d'autorisation
```

Documentation interactive de l'API : `http://localhost:8000/docs`.

## Tests

```
pytest -q
```

## Comptes d'essai

```
python -m outils.reinitialiser_essais     # repart de zéro (sauvegarde l'ancienne base dans sauvegardes/)
python -m outils.creer_comptes_essai --lister
```

Les comptes d'essai ont tous le mot de passe `fama1234` : à n'utiliser que sur une base d'essai.
