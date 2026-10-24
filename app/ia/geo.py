"""Calculs geographiques simples."""
import math


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance a vol d'oiseau entre deux points (latitude, longitude), formule de haversine."""
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))