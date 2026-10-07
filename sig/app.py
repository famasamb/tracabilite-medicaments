"""Application SIG de la PNA: tableau de bord du circuit public (fiche 10), en lecture seule.

Lancer depuis la racine du projet (l'API doit tourner):
    python -m streamlit run sig/app.py
"""
import sys
from pathlib import Path

# Streamlit ajoute le dossier du script au chemin de recherche, pas la racine du projet.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402
import streamlit.components.v1 as composants  # noqa: E402

from sig.carte import COULEURS, html_de_la_carte  # noqa: E402
from sig.client import ClientAPI, ErreurAPI  # noqa: E402

ADRESSE_PAR_DEFAUT = "http://127.0.0.1:8000"
TOUS = "Tous les SR"
LEGENDE = {"expedition": "bleu", "reception": "orange", "dispensation": "vert"}


def page_connexion() -> None:
    st.title("Tracabilite des medicaments")
    st.subheader("Vue de la PNA")
    with st.form("connexion"):
        adresse = st.text_input("Adresse de l'API", ADRESSE_PAR_DEFAUT)
        identifiant = st.text_input("Identifiant de connexion")
        mot_de_passe = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter"):
            try:
                client = ClientAPI.vers(adresse)
                profil = client.connecter(identifiant, mot_de_passe)
            except ErreurAPI as e:
                st.error(e.message)
            else:
                st.session_state.update(client=client, profil=profil)
                st.rerun()


def afficher_tableau(client: ClientAPI) -> None:
    sr = client.liste_sr()
    noms = {s["nom"]: s["id"] for s in sr}
    col1, col2 = st.columns(2)
    choix = col1.selectbox("Service regional", [TOUS, *noms])
    periode = col2.date_input("Periode (du, au)", value=())
    du, au = (periode[0], periode[1]) if len(periode) == 2 else (None, None)

    try:
        t = client.tableau(noms.get(choix), du, au)
    except ErreurAPI as e:
        st.error(e.message)
        return

    st.info(t["avertissement"])
    if t["message"]:                                  # variante 4b: aucun evenement pour ce filtre
        st.warning(t["message"])
        return
    m1, m2, m3 = st.columns(3)
    m1.metric("Evenements", t["nombreEvenements"])
    m2.metric("Unites suivies", t["unitesSuivies"])
    m3.metric("Anomalies signalees", t["anomaliesSignalees"])
    if t["anomaliesParType"]:
        st.bar_chart(t["anomaliesParType"])

    st.subheader("Carte")
    composants.html(html_de_la_carte(t["pointsCarte"]), height=520)
    st.caption("  ".join(f"{LEGENDE[k]} : {k}" for k in COULEURS) +
               f"  -  {len(t['pointsCarte'])} point(s) affiche(s)")

    st.subheader("Alertes recentes")
    if t["alertesRecentes"]:
        st.dataframe(t["alertesRecentes"], hide_index=True, use_container_width=True)
    else:
        st.write("Aucune alerte pour ce filtre.")


def main() -> None:
    st.set_page_config(page_title="Vue de la PNA", layout="wide")
    if "client" not in st.session_state:
        page_connexion()
        return
    profil = st.session_state["profil"]
    st.sidebar.write(f"{profil['nom']}  \n{profil['structure_nom']}")
    if st.sidebar.button("Se deconnecter"):
        st.session_state.clear()
        st.rerun()
    st.title("Circuit public: tableau de bord")
    afficher_tableau(st.session_state["client"])


main()