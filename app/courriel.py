"""Envoi de courriels (reinitialisation de mot de passe).

Configuration par variables d'environnement:
  SMTP_HOTE, SMTP_PORT (587 par defaut), SMTP_UTILISATEUR, SMTP_MOT_DE_PASSE,
  SMTP_EXPEDITEUR (adresse d'expedition; par defaut SMTP_UTILISATEUR),
  SMTP_SECURISE ("starttls" par defaut, ou "ssl" pour le port 465).
Sans SMTP_HOTE (mode developpement), le courriel est affiche dans la console du serveur au lieu d'etre envoye.
"""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

journal = logging.getLogger("tracabilite.courriel")


def url_publique() -> str:
    """Adresse de base de l'application, utilisee dans les liens des courriels."""
    return os.getenv("URL_PUBLIQUE", "http://localhost:8000").rstrip("/")


def envoyer(destinataire: str, sujet: str, texte: str) -> None:
    """Envoie un courriel. Ne leve jamais d'exception: un echec d'envoi est journalise."""
    hote = os.getenv("SMTP_HOTE")
    if not hote:
        print(f"\n===== COURRIEL NON ENVOYE (SMTP non configure) =====\nA: {destinataire}\nObjet: {sujet}\n\n{texte}\n====================================================\n", flush=True)
        return
    utilisateur = os.getenv("SMTP_UTILISATEUR")
    message = EmailMessage()
    message["From"] = os.getenv("SMTP_EXPEDITEUR") or utilisateur or "noreply@localhost"
    message["To"] = destinataire
    message["Subject"] = sujet
    message.set_content(texte)
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        contexte = ssl.create_default_context()
        if os.getenv("SMTP_SECURISE", "starttls").lower() == "ssl":
            serveur = smtplib.SMTP_SSL(hote, port, context=contexte, timeout=15)
        else:
            serveur = smtplib.SMTP(hote, port, timeout=15)
            serveur.starttls(context=contexte)
        with serveur:
            if utilisateur:
                serveur.login(utilisateur, os.getenv("SMTP_MOT_DE_PASSE", ""))
            serveur.send_message(message)
    except Exception:  # noqa: BLE001 - l'echec ne doit jamais remonter a l'utilisateur
        journal.exception("Echec d'envoi du courriel")
