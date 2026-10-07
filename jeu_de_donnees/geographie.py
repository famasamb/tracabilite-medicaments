"""Positions des villes du Senegal pour simuler les deplacements (valeurs approchees du centre-ville)."""
from app.geo import distance_km  # noqa: F401  (le calcul vit dans l'application, le jeu de donnees le reutilise)

# (latitude, longitude). Les noms sont ceux de la colonne `localisation` de data/sr_a_verifier.csv.
VILLES = {
    "Dakar": (14.6937, -17.4441),
    "Diourbel": (14.6553, -16.2314),
    "Fatick": (14.3390, -16.4111),
    "Kaffrine": (14.1052, -15.5508),
    "Kaolack": (14.1470, -16.0726),
    "Kedougou": (12.5579, -12.1743),
    "Kolda": (12.8833, -14.9500),
    "Louga": (15.6144, -16.2246),
    "Matam": (15.6559, -13.2554),
    "Saint-Louis": (16.0179, -16.4896),
    "Sedhiou": (12.7081, -15.5569),
    "Tambacounda": (13.7707, -13.6673),
    "Thies": (14.7910, -16.9359),
    "Ziguinchor": (12.5833, -16.2719),
}