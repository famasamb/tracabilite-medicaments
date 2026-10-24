"""Envoi de courriels (reinitialisation de mot de passe).

Configuration par variables d'environnement:
  SMTP_HOTE, SMTP_PORT (587 par defaut), SMTP_UTILISATEUR, SMTP_MOT_DE_PASSE,
  SMTP_EXPEDITEUR (adresse d'expedition; par defaut SMTP_UTILISATEUR),
  SMTP_NOM_EXPEDITEUR (nom affiche; par defaut "Tracabilite des medicaments"),
  SMTP_SECURISE ("starttls" par defaut, ou "ssl" pour le port 465).
Sans SMTP_HOTE (mode developpement), le courriel est affiche dans la console du serveur au lieu d'etre envoye.
"""
import html
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

journal = logging.getLogger("tracabilite.courriel")


def url_publique() -> str:
    """Adresse de base de l'application, utilisee dans les liens des courriels."""
    return os.getenv("URL_PUBLIQUE", "http://localhost:8000").rstrip("/")


def envoyer(destinataire: str, sujet: str, texte: str, page_html: str | None = None) -> None:
    """Envoie un courriel (texte, et version HTML si fournie). Ne leve jamais d'exception: un echec est journalise."""
    hote = os.getenv("SMTP_HOTE")
    if not hote:
        print(f"\n===== COURRIEL NON ENVOYE (SMTP non configure) =====\nA: {destinataire}\nObjet: {sujet}\n\n{texte}\n====================================================\n", flush=True)
        return
    utilisateur = os.getenv("SMTP_UTILISATEUR")
    message = EmailMessage()
    adresse = os.getenv("SMTP_EXPEDITEUR") or utilisateur or "noreply@localhost"
    message["From"] = formataddr((os.getenv("SMTP_NOM_EXPEDITEUR", "Traçabilité des médicaments"), adresse))
    message["To"] = destinataire
    message["Subject"] = sujet
    message.set_content(texte)
    if page_html:
        message.add_alternative(page_html, subtype="html")
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


def gabarit(titre: str, paragraphes: list[str], bouton: tuple[str, str] | None = None, pied: str = "") -> tuple[str, str]:
    """Fabrique un courriel sobre en deux versions: texte brut et HTML (bouton, couleurs de l'application)."""
    e = html.escape
    texte = f"{titre}\n\n" + "\n\n".join(paragraphes)
    corps = "".join(f'<p style="margin:0 0 16px;font-size:16px;line-height:1.55;color:#0e1f1b">{e(p)}</p>' for p in paragraphes)
    if bouton:
        libelle, lien = bouton
        texte += f"\n\n{libelle} :\n{lien}"
        corps += (f'<p style="margin:26px 0"><a href="{e(lien, quote=True)}" style="display:inline-block;background:#0b5d4b;color:#ffffff;'
                  f'text-decoration:none;font-weight:700;font-size:16px;padding:14px 26px;border-radius:12px">{e(libelle)}</a></p>'
                  f'<p style="margin:0 0 16px;font-size:13px;line-height:1.5;color:#566660">Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>'
                  f'<span style="word-break:break-all">{e(lien)}</span></p>')
    if pied:
        texte += f"\n\n{pied}"
        corps += f'<p style="margin:22px 0 0;padding-top:16px;border-top:1px solid #dce3de;font-size:13px;line-height:1.5;color:#566660">{e(pied)}</p>'
    page = (f'<!doctype html><html lang="fr"><body style="margin:0;background:#f3f5f2;font-family:Arial,Helvetica,sans-serif">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">'
            f'<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden">'
            f'<tr><td style="background:#06382e;padding:22px 28px;color:#ffffff;font-size:17px;font-weight:700">Traçabilité des médicaments</td></tr>'
            f'<tr><td style="padding:28px"><h1 style="margin:0 0 18px;font-size:22px;color:#06382e">{e(titre)}</h1>{corps}</td></tr>'
            f'</table></td></tr></table></body></html>')
    return texte, page
