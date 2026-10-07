"""Carte des evenements du circuit public (fiche 10, etape 3: points geolocalises)."""
import folium

# Position et zoom par defaut: le Senegal entier, quand il n'y a aucun point a montrer
CENTRE_SENEGAL = (14.5, -14.5)
ZOOM_SENEGAL = 7

# Une couleur par type d'operation (distinguables aussi par le texte de l'info-bulle)
COULEURS = {"expedition": "#1f77b4", "reception": "#d95f02", "dispensation": "#1b9e77"}
COULEUR_INCONNUE = "#666666"


def construire_carte(points: list[dict]) -> folium.Map:
    """Un cercle par evenement geolocalise. `points` est la liste `pointsCarte` du tableau de bord."""
    carte = folium.Map(location=CENTRE_SENEGAL, zoom_start=ZOOM_SENEGAL, tiles="OpenStreetMap", control_scale=True)
    for p in points:
        couleur = COULEURS.get(p["typeOperation"], COULEUR_INCONNUE)
        folium.CircleMarker(
            location=(p["latitude"], p["longitude"]), radius=6, color=couleur, weight=1,
            fill=True, fill_color=couleur, fill_opacity=0.7,
            tooltip=f"{p['typeOperation']} - {p['sr']}",
            popup=f"{p['sr']}<br>{p['typeOperation']}<br>{p['dateHeure']}",
        ).add_to(carte)
    if points:
        carte.fit_bounds([(p["latitude"], p["longitude"]) for p in points], padding=(30, 30), max_zoom=12)
    return carte


def html_de_la_carte(points: list[dict]) -> str:
    """Page HTML complete de la carte, a afficher dans un cadre.

    On n'utilise pas `_repr_html_`: c'est la version pour les notebooks Jupyter, qui affiche
    "Make this Notebook Trusted" dans un cadre ordinaire au lieu de la carte."""
    return construire_carte(points).get_root().render()