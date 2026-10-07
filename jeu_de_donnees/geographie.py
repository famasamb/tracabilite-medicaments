"""Positions des villes du Senegal pour simuler les deplacements (valeurs approchees du centre-ville)."""
import math

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


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance a vol d'oiseau entre deux points (latitude, longitude), formule de haversine."""
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))