// Application mobile de traçabilité des médicaments.
// Écrans: connexion (fiche 1), accueil, réception et expédition (fiche 7), dispensation (fiche 8),
// statut d'une unité (fiche 9), compte. Tout passe par l'API, sur la même adresse que cette page.

import { carte } from "./carte.js";

const racine = document.getElementById("appli");

/* ------------------------------------------------------------------ Données du métier */

const TYPES_STRUCTURE = {
  fabricant: "Fabricant",
  grossisteRepartiteur: "Grossiste répartiteur",
  SR: "Service régional",
  officine: "Officine",
  PNA: "Pharmacie nationale",
};

// Mêmes droits que l'API (OPERATIONS_AUTORISEES). L'API reste la référence: elle refuse le reste.
const AUTORISEES = {
  fabricant: ["expedition", "statut"],
  grossisteRepartiteur: ["reception", "expedition", "statut"],
  SR: ["reception", "expedition", "statut"],
  officine: ["reception", "dispensation", "statut"],
};
const PRINCIPALE = { fabricant: "expedition", grossisteRepartiteur: "reception", SR: "reception", officine: "dispensation" };

const OPERATIONS = {
  reception: {
    titre: "Réception", icone: "reception", resume: "Scanner les unités qui arrivent",
    succes: "Réception enregistrée", alerte: "Réception enregistrée, à vérifier",
    lien: "/evenements", consigne: "Cadrez le code DataMatrix de l'unité reçue",
  },
  expedition: {
    titre: "Expédition", icone: "expedition", resume: "Scanner les unités qui partent",
    succes: "Expédition enregistrée", alerte: "Expédition enregistrée, à vérifier",
    lien: "/evenements", consigne: "Cadrez le code DataMatrix de l'unité expédiée",
  },
  dispensation: {
    titre: "Dispensation", icone: "dispensation", resume: "Remettre une unité au patient",
    succes: "Dispensation enregistrée", alerte: "Dispensation enregistrée, à vérifier",
    lien: "/dispensations", consigne: "Cadrez le code DataMatrix de l'unité remise",
  },
  statut: {
    titre: "Vérifier une unité", icone: "verifier", resume: "Statut et dernier mouvement d'une unité",
    lien: "/unites/statut", consigne: "Cadrez le code DataMatrix de l'unité à vérifier",
  },
};

const ANOMALIES = {
  reutilisationIdentifiant: "Réutilisation d'identifiant",
  ruptureSequence: "Rupture de séquence",
  trajetInhabituel: "Trajet inhabituel",
  concentrationInhabituelle: "Concentration inhabituelle",
};
const LECTURES = { classique: "Lecture classique", deep_learning: "Retrouvé par l'IA (YOLOv8)", saisie: "Saisie manuelle" };
const AVIS = "Une alerte est un signal à faire vérifier par une personne, pas une fraude confirmée.";

/* ------------------------------------------------------------------ Icônes */

const trait = (corps, taille = 24) =>
  `<svg width="${taille}" height="${taille}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${corps}</svg>`;

const ICONES = {
  reception: (t) => trait('<path d="M12 3v10m0 0-4-4m4 4 4-4"/><path d="M4 14v3a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-3"/>', t),
  expedition: (t) => trait('<path d="M12 14V4m0 0L8 8m4-4 4 4"/><path d="M4 14v3a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-3"/>', t),
  dispensation: (t) => trait('<rect x="2.5" y="8.5" width="19" height="7" rx="3.5" transform="rotate(-45 12 12)"/><path d="m9.2 9.2 5.6 5.6"/>', t),
  verifier: (t) => trait('<path d="M12 3 5 6v5.5c0 4.4 3 7.6 7 9.5 4-1.9 7-5.1 7-9.5V6l-7-3Z"/><path d="m9 12 2.2 2.2L15.5 10"/>', t),
  accueil: (t) => trait('<path d="M4 11 12 4l8 7"/><path d="M6 10v9h12v-9"/>', t),
  cadenas: (t) => trait('<rect x="5" y="10.5" width="14" height="9.5" rx="2.6"/><path d="M8.2 10.5V8a3.8 3.8 0 0 1 7.6 0v2.5M12 14.4v2"/>', t),
  flecheLongue: (t) => trait('<path d="M4.5 12h15m-5.5-5.5L19.5 12 14 17.5"/>', t),
  compte: (t) => trait('<circle cx="12" cy="8" r="3.6"/><path d="M5 20c.8-3.6 3.6-5.4 7-5.4s6.2 1.8 7 5.4"/>', t),
  fleche: (t) => trait('<path d="m9 6 6 6-6 6"/>', t),
  retour: (t) => trait('<path d="m15 6-6 6 6 6"/>', t),
  oeil: (t) => trait('<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>', t),
  oeilBarre: (t) => trait('<path d="M3 3l18 18"/><path d="M10.6 6A9.7 9.7 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a16 16 0 0 1-3 3.8M6.6 7.6A16 16 0 0 0 2.5 12S6 18.5 12 18.5a9 9 0 0 0 4-.9"/>', t),
  lampe: (t) => trait('<path d="M8 3h8l-1.5 6h-5L8 3Z"/><path d="M9.5 9 8 21h8l-1.5-12"/>', t),
  galerie: (t) => trait('<rect x="3.5" y="4.5" width="17" height="15" rx="3"/><circle cx="9" cy="10" r="1.6"/><path d="m4 17 5-4.5 4 3 3-2.5 4 3.5"/>', t),
  clavier: (t) => trait('<rect x="2.5" y="6" width="19" height="12" rx="3"/><path d="M6.5 10h.01M10 10h.01M13.5 10h.01M17 10h.01M7 14h10"/>', t),
  fermer: (t) => trait('<path d="M6 6l12 12M18 6 6 18"/>', t),
  coche: (t) => trait('<path d="m5 12.5 4.5 4.5L19 7.5"/>', t),
  attention: (t) => trait('<path d="M12 4 2.8 19.5h18.4L12 4Z"/><path d="M12 10v4.2M12 17.2h.01"/>', t),
  croix: (t) => trait('<path d="M6 6l12 12M18 6 6 18"/>', t),
  deconnexion: (t) => trait('<path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3"/><path d="M15 8l4 4-4 4M19 12H9"/>', t),
  produit: (t) => trait('<path d="M4 8.5 12 4l8 4.5v7L12 20l-8-4.5v-7Z"/><path d="m4 8.5 8 4.5 8-4.5M12 13v7"/>', t),
  grille: (t) => trait('<path d="M4 4v16h16"/><path d="M4 4h16M20 4v16" stroke-dasharray="2.5 2.5"/><path d="M9 9h2.5v2.5H9zM13.5 13.5H16V16h-2.5z"/>', t),
  employe: (t) => trait('<circle cx="10" cy="8" r="3.4"/><path d="M3.5 20c.7-3.4 3.2-5.2 6.5-5.2M18 12v6M15 15h6"/>', t),
  batiment: (t) => trait('<path d="M5 20V6l7-3 7 3v14"/><path d="M3 20h18M9 9h.01M9 13h.01M15 9h.01M15 13h.01M10.5 20v-3.5h3V20"/>', t),
  cle: (t) => trait('<circle cx="8" cy="15" r="4"/><path d="m11 12 8-8m-3 3 3 3"/>', t),
  courriel: (t) => trait('<rect x="3" y="5.5" width="18" height="13" rx="2.5"/><path d="m4 8 8 5.5L20 8"/>', t),
  plus: (t) => trait('<path d="M12 5v14M5 12h14"/>', t),
  telecharger: (t) => trait('<path d="M12 4v11m0 0-4-4m4 4 4-4"/><path d="M5 19h14"/>', t),
  loupe: (t) => trait('<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>', t),
  scan: (t) => trait('<path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>', t),
};
const icone = (nom, taille = 24) => ICONES[nom](taille);

// La marque: les quatre coins d'un scan autour d'une pilule dont une moitié se découpe en modules de code
function marque(taille = 32) {
  return `<svg class="marque" width="${taille}" height="${taille}" viewBox="0 0 64 64" fill="none" aria-hidden="true">
    <path d="M10 21V10h11M43 10h11v11M54 43v11H43M21 54H10V43" stroke="currentColor" stroke-width="4" stroke-linecap="square"/>
    <g transform="rotate(-45 32 32)" fill="currentColor"><path d="M35 24H25a8 8 0 0 0 0 16h10z"/><rect x="37.0" y="24.0" width="4.2" height="4.2" /><rect x="37.0" y="29.8" width="4.2" height="4.2" /><rect x="37.0" y="35.6" width="4.2" height="4.2" /><rect x="42.8" y="24.0" width="4.2" height="4.2" /><rect x="42.8" y="29.8" width="4.2" height="4.2" /><rect x="48.6" y="24.0" width="4.2" height="4.2" /></g></svg>`;
}

// Le motif de l'application: un DataMatrix en filigrane (la trame est dessinée en CSS)
function motif() {
  return `<svg class="motif" viewBox="0 0 16 16" shape-rendering="crispEdges" fill="currentColor" aria-hidden="true"><path d="M0 0h1v1h-1zM2 0h1v1h-1zM4 0h1v1h-1zM6 0h1v1h-1zM8 0h1v1h-1zM10 0h1v1h-1zM12 0h1v1h-1zM14 0h1v1h-1zM15 0h1v1h-1zM0 1h1v1h-1zM1 1h1v1h-1zM2 1h1v1h-1zM4 1h1v1h-1zM6 1h1v1h-1zM7 1h1v1h-1zM9 1h1v1h-1zM10 1h1v1h-1zM11 1h1v1h-1zM12 1h1v1h-1zM13 1h1v1h-1zM0 2h1v1h-1zM1 2h1v1h-1zM2 2h1v1h-1zM6 2h1v1h-1zM8 2h1v1h-1zM10 2h1v1h-1zM11 2h1v1h-1zM12 2h1v1h-1zM13 2h1v1h-1zM15 2h1v1h-1zM0 3h1v1h-1zM1 3h1v1h-1zM4 3h1v1h-1zM6 3h1v1h-1zM7 3h1v1h-1zM8 3h1v1h-1zM10 3h1v1h-1zM11 3h1v1h-1zM13 3h1v1h-1zM14 3h1v1h-1zM0 4h1v1h-1zM3 4h1v1h-1zM8 4h1v1h-1zM10 4h1v1h-1zM11 4h1v1h-1zM13 4h1v1h-1zM14 4h1v1h-1zM15 4h1v1h-1zM0 5h1v1h-1zM1 5h1v1h-1zM6 5h1v1h-1zM10 5h1v1h-1zM13 5h1v1h-1zM0 6h1v1h-1zM1 6h1v1h-1zM6 6h1v1h-1zM7 6h1v1h-1zM9 6h1v1h-1zM10 6h1v1h-1zM11 6h1v1h-1zM12 6h1v1h-1zM13 6h1v1h-1zM15 6h1v1h-1zM0 7h1v1h-1zM1 7h1v1h-1zM2 7h1v1h-1zM3 7h1v1h-1zM5 7h1v1h-1zM6 7h1v1h-1zM11 7h1v1h-1zM12 7h1v1h-1zM13 7h1v1h-1zM0 8h1v1h-1zM2 8h1v1h-1zM3 8h1v1h-1zM4 8h1v1h-1zM5 8h1v1h-1zM6 8h1v1h-1zM8 8h1v1h-1zM9 8h1v1h-1zM10 8h1v1h-1zM11 8h1v1h-1zM15 8h1v1h-1zM0 9h1v1h-1zM4 9h1v1h-1zM9 9h1v1h-1zM10 9h1v1h-1zM11 9h1v1h-1zM13 9h1v1h-1zM14 9h1v1h-1zM0 10h1v1h-1zM1 10h1v1h-1zM2 10h1v1h-1zM3 10h1v1h-1zM4 10h1v1h-1zM5 10h1v1h-1zM6 10h1v1h-1zM7 10h1v1h-1zM8 10h1v1h-1zM9 10h1v1h-1zM12 10h1v1h-1zM13 10h1v1h-1zM14 10h1v1h-1zM15 10h1v1h-1zM0 11h1v1h-1zM1 11h1v1h-1zM2 11h1v1h-1zM5 11h1v1h-1zM6 11h1v1h-1zM7 11h1v1h-1zM8 11h1v1h-1zM9 11h1v1h-1zM10 11h1v1h-1zM12 11h1v1h-1zM13 11h1v1h-1zM0 12h1v1h-1zM2 12h1v1h-1zM4 12h1v1h-1zM9 12h1v1h-1zM10 12h1v1h-1zM11 12h1v1h-1zM15 12h1v1h-1zM0 13h1v1h-1zM1 13h1v1h-1zM2 13h1v1h-1zM9 13h1v1h-1zM11 13h1v1h-1zM12 13h1v1h-1zM13 13h1v1h-1zM14 13h1v1h-1zM0 14h1v1h-1zM1 14h1v1h-1zM4 14h1v1h-1zM8 14h1v1h-1zM9 14h1v1h-1zM10 14h1v1h-1zM11 14h1v1h-1zM12 14h1v1h-1zM15 14h1v1h-1zM0 15h1v1h-1zM1 15h1v1h-1zM2 15h1v1h-1zM3 15h1v1h-1zM4 15h1v1h-1zM5 15h1v1h-1zM6 15h1v1h-1zM7 15h1v1h-1zM8 15h1v1h-1zM9 15h1v1h-1zM10 15h1v1h-1zM11 15h1v1h-1zM12 15h1v1h-1zM13 15h1v1h-1zM14 15h1v1h-1zM15 15h1v1h-1z"/></svg>`;
}

/* ------------------------------------------------------------------ État et stockage */

const etat = { jeton: null, profil: null, resultat: null, nettoyage: null, produit: null };

function lire(cle) { try { return JSON.parse(localStorage.getItem(cle)); } catch { return null; } }
function ecrire(cle, valeur) { try { localStorage.setItem(cle, JSON.stringify(valeur)); } catch { /* stockage indisponible */ } }
function effacer(cle) { try { localStorage.removeItem(cle); } catch { /* idem */ } }

function restaurerSession() {
  const s = lire("session");
  if (s && s.jeton && s.profil) { etat.jeton = s.jeton; etat.profil = s.profil; }
}
function fermerSession() {
  etat.jeton = etat.profil = etat.resultat = null;
  effacer("session");
  aller("#/connexion");
}

const cleRecents = () => `recents:${etat.profil.id}`;
function recents() { return lire(cleRecents()) || []; }
function noterRecent(entree) {
  const liste = [entree, ...recents()].slice(0, 200);
  ecrire(cleRecents(), liste);
}

/* ------------------------------------------------------------------ API */

class ErreurApi extends Error {
  constructor(statut, detail) { super(detail || `Erreur ${statut}`); this.statut = statut; this.detail = detail || ""; }
}

async function requete(chemin, { methode = "GET", corps, formulaire, json } = {}) {
  const entetes = {};
  if (etat.jeton) entetes.Authorization = `Bearer ${etat.jeton}`;
  if (json !== undefined) entetes["Content-Type"] = "application/json";
  let reponse;
  try {
    reponse = await fetch(chemin, { method: methode, headers: entetes, body: json !== undefined ? JSON.stringify(json) : formulaire || corps });
  } catch {
    throw new ErreurApi(0, "reseau");
  }
  if (!reponse.ok) {
    let donnees = null;
    try { donnees = await reponse.json(); } catch { /* corps vide ou non JSON */ }
    const d = donnees && donnees.detail;
    const detail = typeof d === "string" ? d : Array.isArray(d) ? "validation" : "";
    throw new ErreurApi(reponse.status, detail);
  }
  return reponse;
}

async function api(chemin, options) {
  const reponse = await requete(chemin, options);
  try { return await reponse.json(); } catch { return null; }
}

/* ------------------------------------------------------------------ Textes d'erreur (en français soigné) */

function texteConnexion(e) {
  if (e.statut === 0) return "Le serveur est injoignable. Vérifiez votre connexion et réessayez.";
  if (/aucun compte/i.test(e.detail)) return "Aucun compte ne correspond à cet identifiant. Contactez le responsable de votre structure.";
  if (/incorrect/i.test(e.detail)) return "Identifiant ou mot de passe incorrect.";
  return e.detail || "Connexion impossible.";
}

function texteScan(e) {
  const d = e.detail;
  if (e.statut === 0) return { titre: "Serveur injoignable", texte: "Vérifiez votre connexion, puis réessayez." };
  if (/illisible/i.test(d)) return { titre: "Code illisible", texte: "Reprenez la photo en rapprochant le code, ou saisissez le numéro de série." };
  if (/inconnu|referencee/i.test(d)) return { titre: "Unité inconnue", texte: "Aucune unité sérialisée ne porte ce numéro. Vérifiez la provenance du produit." };
  if (/volumineuse/i.test(d)) return { titre: "Image trop volumineuse", texte: "La photo dépasse 5 Mo. Reprenez-la." };
  if (/envoyez l'image/i.test(d)) return { titre: "Aucun code reçu", texte: "Photographiez le code ou saisissez le numéro de série." };
  if (/serialisee par votre structure/i.test(d)) return { titre: "Unité d'une autre structure", texte: "Cette unité n'a pas été sérialisée par votre structure." };
  if (e.statut === 403) return { titre: "Opération non autorisée", texte: "Votre structure n'est pas autorisée à effectuer cette opération." };
  return { titre: "Opération impossible", texte: d || "Une erreur est survenue. Réessayez." };
}

/* ------------------------------------------------------------------ Utilitaires d'affichage */

const echapper = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const initiales = (nom) => nom.split(/\s+/).filter(Boolean).slice(-2).map((m) => m[0]).join("").toUpperCase();
// L'API renvoie des dates UTC sans fuseau
const date = (iso) => new Date(/Z|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
const dateLongue = (iso) => date(iso).toLocaleString("fr-FR", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Africa/Dakar" });
function ilYA(iso) {
  const min = Math.round((Date.now() - date(iso)) / 60000);
  if (min < 1) return "à l'instant";
  if (min < 60) return `il y a ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `il y a ${h} h`;
  return date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short", timeZone: "Africa/Dakar" });
}
const vibrer = (motif) => { try { navigator.vibrate?.(motif); } catch { /* non pris en charge */ } };

/* ------------------------------------------------------------------ Navigation */

function aller(hash) { if (location.hash === hash) rendre(); else location.hash = hash; }

function rendre() {
  etat.nettoyage?.(); etat.nettoyage = null;
  const hash = location.hash || "#/";
  if (hash === "#/inscription") { vueInscription(); return; }
  if (hash === "#/mot-de-passe-oublie") { vueMotDePasseOublie(); return; }
  const lien = hash.match(/^#\/reinitialiser(?:\/([\w-]+))?$/);
  if (lien && (lien[1] || lireJetonLien())) { vueReinitialiser(lien[1] || lireJetonLien()); return; }
  if (!etat.jeton) { vueConnexion(); return; }
  if (hash === "#/connexion") { aller("#/"); return; }
  const p = etat.profil, type = p.structure_type;
  const m = hash.match(/^#\/scan\/(\w+)$/);
  if (m && OPERATIONS[m[1]] && operationsScan().includes(m[1])) { vueScanner(m[1]); return; }
  if (hash === "#/resultat" && etat.resultat) { vueResultat(); return; }
  if (hash === "#/compte") { vueCompte(); return; }
  if (hash === "#/compte/mot-de-passe") { vueMotDePasse(); return; }
  if (hash === "#/compte/courriel") { vueCourriel(); return; }
  if (type === "fabricant") {
    if (hash === "#/produits") { vueProduits(); return; }
    if (hash === "#/produits/nouveau") { vueProduitNouveau(); return; }
    if (hash === "#/lot") { vueLot(); return; }
  }
  if (p.role === "responsable") {
    if (hash === "#/equipe") { vueEquipe(); return; }
    if (type === "PNA" && hash === "#/sr") { vueSR(); return; }
    const sr = hash.match(/^#\/sr\/(\w+)$/);
    if (type === "PNA" && sr) { vueSRResponsable(sr[1]); return; }
  }
  vueAccueil();
}

/* ------------------------------------------------------------------ Connexion */

function vueConnexion(erreur = "") {
  racine.innerHTML = `
    <div class="connexion">
    <header class="connexion-tete">
      ${carte()}
      <div class="contenu">
        ${marque(46)}
        <h1>Traçabilité des médicaments</h1>
        <p>De la fabrication à la dispensation.</p>
      </div>
    </header>
    <main class="connexion-corps">
      <h2 class="connexion-titre">Se connecter</h2>
      <p class="connexion-aide">Identifiant choisi à l'inscription, ou remis par le responsable de votre structure.</p>
      <form id="formulaire" novalidate>
        <div id="erreur" role="alert">${erreur ? blocErreur(erreur) : ""}</div>
        <label class="champ"><span>Identifiant de connexion</span>
          <div class="saisie"><span class="pre">${icone("compte", 22)}</span><input name="identifiant" autocomplete="username" autocapitalize="none" spellcheck="false" value="${echapper(identifiantInitial)}" required></div>
        </label>
        <label class="champ"><span>Mot de passe</span>
          <div class="saisie"><span class="pre">${icone("cadenas", 22)}</span><input name="mdp" type="password" autocomplete="current-password" required>
            <button type="button" class="oeil" data-action="oeil" aria-label="Afficher le mot de passe">${icone("oeil")}</button></div>
        </label>
        <p class="oubli"><a href="#/mot-de-passe-oublie">Mot de passe oublié ?</a></p>
        <button class="bouton" type="submit">Se connecter ${icone("flecheLongue", 22)}</button>
      </form>
      <div class="ou" role="separator"><span>Ou</span></div>
      <a class="bouton contour" href="#/inscription">${icone("batiment", 22)}Inscrire ma structure</a>
      </main></div>`;
  const formulaire = document.getElementById("formulaire");
  (identifiantInitial ? formulaire.mdp : formulaire.identifiant).focus({ preventScroll: true });
  formulaire.querySelector('[data-action="oeil"]').addEventListener("click", (ev) => {
    const visible = formulaire.mdp.type === "text";
    formulaire.mdp.type = visible ? "password" : "text";
    ev.currentTarget.innerHTML = icone(visible ? "oeil" : "oeilBarre");
    ev.currentTarget.setAttribute("aria-label", visible ? "Afficher le mot de passe" : "Masquer le mot de passe");
  });
  formulaire.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const zone = document.getElementById("erreur"), bouton = formulaire.querySelector(".bouton");
    const identifiant = formulaire.identifiant.value.trim(), mdp = formulaire.mdp.value;
    if (!identifiant || !mdp) { zone.innerHTML = blocErreur("Saisissez votre identifiant et votre mot de passe."); return; }
    bouton.disabled = true; bouton.textContent = "Connexion…"; zone.innerHTML = "";
    try {
      const corps = new URLSearchParams({ username: identifiant, password: mdp });
      const jeton = (await api("/auth/connexion", { methode: "POST", corps })).access_token;
      etat.jeton = jeton;
      const profil = await api("/auth/moi");
      etat.profil = profil;
      ecrire("session", { jeton, profil });
      aller("#/");
    } catch (e) {
      etat.jeton = etat.profil = null;
      zone.innerHTML = blocErreur(texteConnexion(e));
      bouton.disabled = false; bouton.innerHTML = `Se connecter ${icone("flecheLongue", 22)}`;
    }
  });
}
const blocErreur = (texte) => `<div class="message-erreur">${icone("attention", 20)}<span>${echapper(texte)}</span></div>`;

/* ------------------------------------------------------------------ Barre du bas et feuille des opérations */

function operationsScan() { return AUTORISEES[etat.profil.structure_type] || []; }

function barre(actif) {
  const scan = operationsScan().length > 0;
  return `<nav class="barre ${scan ? "" : "sans-scan"}" aria-label="Navigation principale">
    <button class="onglet" data-aller="#/" ${actif === "accueil" ? 'aria-current="page"' : ""}>${icone("accueil")}Accueil</button>
    ${scan ? `<button class="bouton-scan" data-action="choisir" aria-label="Scanner une unité">${icone("scan", 30)}</button>` : ""}
    <button class="onglet" data-aller="#/compte" ${actif === "compte" ? 'aria-current="page"' : ""}>${icone("compte")}Compte</button>
  </nav>`;
}

function brancherBarre() {
  racine.querySelectorAll("[data-aller]").forEach((b) => b.addEventListener("click", () => aller(b.dataset.aller)));
  racine.querySelector('[data-action="choisir"]')?.addEventListener("click", ouvrirChoix);
}

function ouvrirChoix() {
  const ops = operationsScan();
  const feuille = document.createElement("div");
  feuille.innerHTML = `<div class="voile" data-fermer></div>
    <section class="feuille" role="dialog" aria-modal="true" aria-label="Que voulez-vous scanner ?">
      <div class="poignee"></div><h2>Que voulez-vous faire ?</h2><p class="aide">Choisissez l'opération, puis cadrez le code de l'unité.</p>
      <div class="actions">${ops.map((o) => ligneAction(o, false)).join("")}</div>
    </section>`;
  document.body.appendChild(feuille);
  const fermer = () => feuille.remove();
  feuille.querySelector("[data-fermer]").addEventListener("click", fermer);
  feuille.querySelectorAll("[data-op]").forEach((b) => b.addEventListener("click", () => { fermer(); aller(`#/scan/${b.dataset.op}`); }));
  feuille.querySelector("[data-op]").focus();
  document.addEventListener("keydown", function sortie(ev) { if (ev.key === "Escape") { fermer(); document.removeEventListener("keydown", sortie); } });
}

function ligneAction(op, principale) {
  const o = OPERATIONS[op];
  return `<button class="action ${principale ? "principale" : ""}" data-op="${op}">
    <span class="tuile">${icone(o.icone, principale ? 30 : 26)}</span>
    <span class="texte"><strong>${o.titre}</strong><small>${o.resume}</small></span>
    <span class="fleche">${icone("fleche", 20)}</span></button>`;
}

/* ------------------------------------------------------------------ Accueil */

function gestion() {
  const p = etat.profil, liste = [];
  if (p.structure_type === "fabricant") {
    liste.push({ vers: "#/produits", icone: "produit", titre: "Produits", resume: "Rechercher ou enregistrer un produit" });
    liste.push({ vers: "#/lot", icone: "grille", titre: "Sérialiser un lot", resume: "Générer les codes à imprimer" });
  }
  if (p.role === "responsable") {
    liste.push({ vers: "#/equipe", icone: "employe", titre: "Ajouter un employé", resume: "Créer un compte pour votre équipe" });
    if (p.structure_type === "PNA") liste.push({ vers: "#/sr", icone: "batiment", titre: "Services régionaux", resume: "Créer le compte responsable d'un SR" });
  }
  return liste;
}

function ligneGestion(g) {
  return `<button class="rang" data-aller="${g.vers}">
    <span class="pastille-icone">${icone(g.icone, 22)}</span>
    <span class="texte"><strong>${g.titre}</strong><small>${g.resume}</small></span>
    <span class="fleche">${icone("fleche", 18)}</span></button>`;
}

function tuileAction(op) {
  const o = OPERATIONS[op];
  return `<button class="tuile-action" data-op="${op}">
    <span class="pastille-icone">${icone(o.icone, 24)}</span>
    <span class="texte"><strong>${o.titre}</strong><small>${o.resume}</small></span></button>`;
}

// En-tête sombre des pages d'accueil et de compte
function heros(haut, corps, classe = "") {
  return `<header class="hero ${classe}">${motif()}
    <div class="hero-haut"><span class="marque">${marque(26)}${haut}</span>${corps.avatar || ""}</div>
    ${corps.titre || ""}</header>`;
}

function vueAccueil() {
  const p = etat.profil, ops = operationsScan(), principale = PRINCIPALE[p.structure_type];
  const liste = ops.length ? recents().slice(0, 5) : [], outils = gestion();
  const autres = ops.filter((o) => o !== principale);
  racine.innerHTML = `
    <main class="accueil">
      ${heros("Traçabilité", {
        avatar: `<button class="avatar" data-aller="#/compte" aria-label="Mon compte">${echapper(initiales(p.nom))}</button>`,
        titre: `<div class="hero-corps"><div class="bonjour">Bonjour, ${echapper(p.nom)}</div>
          <h1>${echapper(p.structure_nom)}</h1>
          <span class="puce claire">${TYPES_STRUCTURE[p.structure_type] || p.structure_type}</span></div>` }, "clair")}
      <div class="accueil-corps">
        ${ops.length ? `<div class="actions">${ligneAction(principale, true)}</div>
        ${autres.length ? `<div class="tuiles">${autres.map(tuileAction).join("")}</div>` : ""}` : ""}
        ${outils.length ? `<h2 class="section-titre">Gestion</h2><div class="groupe">${outils.map(ligneGestion).join("")}</div>` : ""}
        ${p.structure_type === "PNA" ? '<p class="encart">Le suivi du circuit public (carte et alertes) se consulte dans la vue SIG.</p>' : ""}
        ${ops.length ? `<h2 class="section-titre">Récents sur cet appareil</h2>
        ${bilanDuJour()}
        ${liste.length ? `<div class="groupe">${liste.map(ligneRecent).join("")}</div>`
          : `<div class="groupe"><div class="vide"><strong>Aucune opération pour l'instant</strong>Les unités que vous scannez apparaîtront ici.</div></div>`}
        ${liste.length ? '<p class="mention">Appuyez sur une unité pour revoir son statut. Liste conservée sur cet appareil seulement.</p>' : ""}` : ""}
      </div>
    </main>${barre("accueil")}`;
  brancherBarre();
  racine.querySelectorAll("[data-op]").forEach((b) => b.addEventListener("click", () => aller(`#/scan/${b.dataset.op}`)));
  racine.querySelectorAll("[data-serie]").forEach((b) => b.addEventListener("click", () => verifierRecent(b.dataset.serie)));
}

// Chiffres du jour, calculés sur les opérations scannées depuis cet appareil
function bilanDuJour() {
  const aujourdhui = new Date().toDateString();
  const jour = recents().filter((r) => date(r.date).toDateString() === aujourdhui);
  if (!jour.length) return "";
  const n = (issue) => jour.filter((r) => r.issue === issue).length;
  const cellule = (classe, valeur, libelle) => `<div class="${classe}${valeur ? "" : " nul"}"><strong>${valeur}</strong><span>${libelle}</span></div>`;
  return `<div class="bilan" aria-label="Aujourd'hui sur cet appareil">${cellule("ok", n("ok"), "Enregistrées")}${cellule("alerte", n("alerte"), "À vérifier")}${cellule("refus", n("refus"), "Refusées")}</div>`;
}

function ligneRecent(r) {
  const o = OPERATIONS[r.op];
  const classe = r.issue === "ok" ? "ok" : r.issue === "alerte" ? "alerte" : "refus";
  const mot = { ok: "Enregistrée", alerte: "À vérifier", refus: "Refusée" }[r.issue];
  const symbole = icone({ ok: "coche", alerte: "attention", refus: "croix" }[r.issue], 20);
  const interieur = `<span class="pastille ${classe}">${symbole}</span>
    <span class="texte"><strong>${o.titre}</strong><small class="id">${echapper(r.serie)}</small></span>
    <span class="droite"><strong class="${classe}">${mot}</strong><time>${ilYA(r.date)}</time></span>`;
  // Une unité dont on connaît le numéro de série peut être revérifiée d'un appui
  return r.serie && r.serie !== "Code scanné"
    ? `<button class="recent" data-serie="${echapper(r.serie)}" aria-label="Voir le statut de l'unité ${echapper(r.serie)}">${interieur}<span class="fleche">${icone("fleche", 18)}</span></button>`
    : `<div class="recent">${interieur}</div>`;
}

// Revérifier une unité déjà scannée sur cet appareil, sans rescanner
async function verifierRecent(serie) {
  const chargement = document.createElement("div");
  chargement.className = "chargement"; chargement.setAttribute("role", "status");
  chargement.innerHTML = '<div><div class="anneau"></div><strong>Vérification…</strong></div>';
  document.body.appendChild(chargement);
  try {
    const f = new FormData(); f.append("numeroSerie", serie);
    const donnees = await api("/unites/statut", { methode: "POST", formulaire: f });
    etat.resultat = { op: "statut", donnees, date: new Date().toISOString() };
    aller("#/resultat");
  } catch (e) {
    if (e.statut === 401) { fermerSession(); return; }
    const { titre, texte } = texteScan(e);
    annoncer(`${titre}. ${texte}`);
  } finally { chargement.remove(); }
}

function annoncer(texte) {
  document.querySelector(".annonce")?.remove();
  const a = document.createElement("div");
  a.className = "annonce"; a.setAttribute("role", "alert"); a.textContent = texte;
  document.body.appendChild(a);
  setTimeout(() => a.remove(), 5000);
}

/* ------------------------------------------------------------------ Compte */

function vueCompte() {
  const p = etat.profil;
  racine.innerHTML = `<main class="accueil">
    ${heros("Compte", {}, "court")}
    <div class="accueil-corps">
      <section class="compte-carte"><div class="avatar">${echapper(initiales(p.nom))}</div>
        <h2>${echapper(p.nom)}</h2><p>${echapper(p.fonction)}</p>
        <p>${echapper(p.structure_nom)}</p><span class="puce">${TYPES_STRUCTURE[p.structure_type] || p.structure_type}</span></section>
      ${p.email
        ? `<p class="courriel-compte">${icone("courriel", 18)}<span>${echapper(p.email)}</span><button class="lien" data-aller="#/compte/courriel">Modifier</button></p>`
        : `<div class="avis-courriel" role="note"><strong>Ajoutez votre adresse e-mail</strong><p>Sans elle, vous ne pourrez pas récupérer votre compte si vous oubliez votre mot de passe.</p><button class="bouton discret" data-aller="#/compte/courriel">Ajouter mon adresse e-mail</button></div>`}
      <div style="margin-top:20px;display:grid;gap:12px"><button class="bouton discret" data-aller="#/compte/mot-de-passe">${icone("cle", 20)}Changer mon mot de passe</button>
      <button class="bouton discret" data-action="sortir">${icone("deconnexion", 20)}Se déconnecter</button></div>
    </div>
  </main>${barre("compte")}`;
  brancherBarre();
  racine.querySelectorAll("[data-aller]").forEach((b) => b.addEventListener("click", () => aller(b.dataset.aller)));
  racine.querySelector('[data-action="sortir"]').addEventListener("click", fermerSession);
}

// Chaque utilisateur change son propre mot de passe
function vueMotDePasse() {
  sousPage("Mot de passe", `
    <form id="formulaire" novalidate>${zoneErreur}
      ${champ("motDePasseActuel", "Mot de passe actuel", { type: "password", mdp: true, autocomplete: "current-password", maxlength: 128 })}
      ${champ("nouveauMotDePasse", "Nouveau mot de passe", { type: "password", mdp: true, autocomplete: "new-password", aide: "8 caractères au moins, différent de l'actuel", maxlength: 128 })}
      ${boutonGenerer}
      ${champ("confirmation", "Confirmer le nouveau mot de passe", { type: "password", mdp: true, autocomplete: "new-password", maxlength: 128 })}
      <button class="bouton" type="submit">Changer le mot de passe</button>
    </form>`, "#/compte");
  const form = document.getElementById("formulaire");
  brancherChamps(form);
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const brut = (n) => form[n].value;
    if (!valider(form, [
      ["motDePasseActuel", requis("Saisissez votre mot de passe actuel.")],
      ["nouveauMotDePasse", (v) => (v.length < 8 ? "Le mot de passe compte au moins 8 caractères." : brut("nouveauMotDePasse") === brut("motDePasseActuel") ? "Choisissez un mot de passe différent de l'actuel." : "")],
      ["confirmation", () => (brut("confirmation") === brut("nouveauMotDePasse") ? "" : "Les deux mots de passe ne sont pas identiques.")],
    ])) return;
    soumettre(form, "Enregistrement…", async () => {
      const r = await api("/auth/mot-de-passe", { methode: "POST", json: { motDePasseActuel: brut("motDePasseActuel"), nouveauMotDePasse: brut("nouveauMotDePasse") } });
      // Les autres appareils sont déconnectés; cet appareil reçoit un nouveau jeton
      etat.jeton = r.access_token; ecrire("session", { jeton: etat.jeton, profil: etat.profil });
      afficherSucces({
        titre: "Mot de passe modifié",
        sous: "Vos autres appareils ont été déconnectés. Utilisez le nouveau mot de passe à votre prochaine connexion.",
        boutons: [{ texte: "Retour au compte", clic: () => aller("#/compte") }],
      });
    });
  });
}


// Adresse e-mail du compte (récupération du mot de passe)
function vueCourriel() {
  sousPage(etat.profil.email ? "Adresse e-mail" : "Ajouter mon e-mail", `
    <p class="intro">Elle sert à vous envoyer un lien si vous oubliez votre mot de passe. Votre mot de passe est demandé pour confirmer.</p>
    <form id="formulaire" novalidate>${zoneErreur}
      ${champCourriel(etat.profil.email || "", "")}
      ${champ("motDePasseActuel", "Votre mot de passe", { type: "password", mdp: true, autocomplete: "current-password", maxlength: 128 })}
      <button class="bouton" type="submit">Enregistrer</button>
    </form>`, "#/compte");
  const form = document.getElementById("formulaire");
  brancherChamps(form);
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (!valider(form, [["email", regleCourriel], ["motDePasseActuel", requis("Saisissez votre mot de passe.")]])) return;
    soumettre(form, "Enregistrement…", async () => {
      const r = await api("/auth/courriel", { methode: "PUT", json: { email: form.email.value.trim(), motDePasseActuel: form.motDePasseActuel.value } });
      etat.profil = { ...etat.profil, email: r.email }; ecrire("session", { jeton: etat.jeton, profil: etat.profil });
      afficherSucces({ titre: "Adresse enregistrée", sous: "Vous pourrez récupérer votre compte à cette adresse.", lignes: [["Adresse e-mail", echapper(r.email), "serie"]],
        boutons: [{ texte: "Retour au compte", clic: () => aller("#/compte") }] });
    });
  });
}

// Pages publiques: mot de passe oublié, puis choix du nouveau mot de passe par le lien reçu
function pagePublique(titre, corps) {
  racine.innerHTML = `<main class="page page-simple">
    <header class="sous-entete"><button class="retour" data-action="retour" aria-label="Retour">${icone("retour")}</button><h1>${titre}</h1></header>
    ${corps}</main>`;
  racine.querySelector('[data-action="retour"]').addEventListener("click", () => aller("#/connexion"));
}

function vueMotDePasseOublie() {
  pagePublique("Mot de passe oublié", `
    <p class="intro">Saisissez l'adresse e-mail de votre compte. Nous vous envoyons un lien, valable 30 minutes, pour choisir un nouveau mot de passe.</p>
    <form id="formulaire" novalidate>${zoneErreur}
      ${champCourriel("", "")}
      <button class="bouton" type="submit">Envoyer le lien</button>
    </form>`);
  const form = document.getElementById("formulaire");
  brancherChamps(form);
  form.email.focus({ preventScroll: true });
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (!valider(form, [["email", regleCourriel]])) return;
    soumettre(form, "Envoi…", async () => {
      await api("/auth/mot-de-passe-oublie", { methode: "POST", json: { email: form.email.value.trim() } });
      afficherSucces({
        titre: "Vérifiez votre messagerie",
        sous: "Si cette adresse correspond à un compte, un e-mail avec le lien vient d'être envoyé. Pensez à regarder les courriers indésirables.",
        boutons: [{ texte: "Retour à la connexion", clic: () => aller("#/connexion") }],
      });
    });
  });
}

// Le jeton du lien est gardé le temps de l'onglet (retour depuis la messagerie, rechargement), pas dans l'historique
const lireJetonLien = () => { try { return sessionStorage.getItem("jetonLien"); } catch { return null; } };
function vueReinitialiser(jeton) {
  try { sessionStorage.setItem("jetonLien", jeton); } catch { /* stockage indisponible */ }
  history.replaceState(null, "", "#/reinitialiser");
  pagePublique("Nouveau mot de passe", `
    <p class="intro">Choisissez un nouveau mot de passe d'au moins 8 caractères.</p>
    <form id="formulaire" novalidate>${zoneErreur}
      ${champ("nouveauMotDePasse", "Nouveau mot de passe", { type: "password", mdp: true, autocomplete: "new-password", maxlength: 128 })}
      ${boutonGenerer}
      ${champ("confirmation", "Confirmer le nouveau mot de passe", { type: "password", mdp: true, autocomplete: "new-password", maxlength: 128 })}
      <button class="bouton" type="submit">Enregistrer le mot de passe</button>
    </form>`);
  const form = document.getElementById("formulaire");
  brancherChamps(form);
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (!valider(form, [
      ["nouveauMotDePasse", regleMdp],
      ["confirmation", () => (form.confirmation.value === form.nouveauMotDePasse.value ? "" : "Les deux mots de passe ne sont pas identiques.")],
    ])) return;
    soumettre(form, "Enregistrement…", async () => {
      await api("/auth/reinitialiser-mot-de-passe", { methode: "POST", json: { jeton, nouveauMotDePasse: form.nouveauMotDePasse.value } });
      etat.jeton = etat.profil = null; effacer("session");
      try { sessionStorage.removeItem("jetonLien"); } catch { /* idem */ }
      afficherSucces({
        titre: "Mot de passe modifié",
        sous: "Vous pouvez vous connecter avec votre nouveau mot de passe.",
        boutons: [{ texte: "Se connecter", clic: () => aller("#/connexion") }],
      });
    });
  });
}

/* ------------------------------------------------------------------ Scanner */

function vueScanner(op) {
  const o = OPERATIONS[op];
  let flux = null, position = null, occupe = false, lampe = false;

  racine.innerHTML = `
    <section class="scanner" aria-label="${o.titre}">
      <video id="video" playsinline muted autoplay class="cache"></video>
      <div id="repli" class="repli"><div><strong>Caméra en attente</strong>Autorisez l'accès à la caméra, ou utilisez une photo ou la saisie du numéro de série.</div></div>
      <div class="scanner-haut">
        <button class="rond" data-action="retour" aria-label="Retour">${icone("retour")}</button>
        <h1>${o.titre}</h1>
        <button class="rond cache" id="lampe" data-action="lampe" aria-pressed="false" aria-label="Lampe torche">${icone("lampe")}</button>
      </div>
      <div id="position" class="position" role="status">Recherche de la position…</div>
      <div class="visee"><div class="cadre">
        <svg viewBox="0 0 100 100" fill="none" preserveAspectRatio="none" aria-hidden="true">
          <path class="plein" d="M2.5 2.5v95h95"/>
          <path class="pointille" d="M2.5 2.5h95"/><path class="pointille" d="M97.5 2.5v95"/>
        </svg><div class="consigne">${o.consigne}</div></div></div>
      <div class="scanner-bas">
        <button class="cote" data-action="galerie">${icone("galerie", 26)}Photo</button>
        <button class="declencheur" data-action="capturer" aria-label="Photographier le code"><span></span></button>
        <button class="cote" data-action="saisie">${icone("clavier", 26)}Saisir</button>
      </div>
      <input type="file" id="fichier" accept="image/*" capture="environment" class="cache">
    </section>`;

  const video = document.getElementById("video");

  // Position GPS: facultative, l'API accepte un événement sans position
  const zonePosition = document.getElementById("position");
  if ("geolocation" in navigator && op !== "statut") {
    navigator.geolocation.getCurrentPosition(
      (p) => { position = { latitude: p.coords.latitude, longitude: p.coords.longitude }; zonePosition.textContent = "Position prête"; zonePosition.className = "position prete"; },
      () => { zonePosition.textContent = "Position indisponible"; zonePosition.className = "position absente"; },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 });
  } else if (op === "statut") {
    zonePosition.classList.add("cache");
  } else { zonePosition.textContent = "Position indisponible"; zonePosition.className = "position absente"; }

  // Caméra
  (async () => {
    if (!navigator.mediaDevices?.getUserMedia) return;
    try {
      flux = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
      video.srcObject = flux; await video.play();
      video.classList.remove("cache"); document.getElementById("repli").classList.add("cache");
      const piste = flux.getVideoTracks()[0];
      if (piste.getCapabilities?.().torch) document.getElementById("lampe").classList.remove("cache");
    } catch { /* refus ou pas de caméra: le repli reste affiché */ }
  })();

  etat.nettoyage = () => { flux?.getTracks().forEach((t) => t.stop()); document.querySelectorAll(".feuille, .voile, .chargement").forEach((n) => n.remove()); };

  async function envoyer({ fichier, serie }) {
    if (occupe) return;
    occupe = true; vibrer(30);
    const chargement = document.createElement("div");
    chargement.className = "chargement"; chargement.setAttribute("role", "status");
    chargement.innerHTML = `<div><div class="anneau"></div><strong>${fichier ? "Lecture du code…" : "Vérification…"}</strong></div>`;
    document.body.appendChild(chargement);
    const f = new FormData();
    if (op === "reception" || op === "expedition") f.append("typeOperation", op);
    if (fichier) { const envoye = await reduireImage(fichier); f.append("image", envoye, envoye.name || "code.jpg"); }
    if (serie) f.append("numeroSerie", serie);
    if (position && op !== "statut") { f.append("latitude", position.latitude); f.append("longitude", position.longitude); }
    try {
      const donnees = await api(o.lien, { methode: "POST", formulaire: f });
      terminer(donnees);
    } catch (e) {
      if (e.statut === 401) { fermerSession(); return; }
      if (op === "dispensation" && e.statut === 409) { terminer(null, e, serie); return; }
      chargement.remove(); occupe = false; vibrer([60, 60, 60]);
      ouvrirErreur(texteScan(e));
    }
  }

  function terminer(donnees, refus, saisie) {
    const resultat = { op, donnees, refus: refus ? refus.detail : null, serie: saisie || "", position: Boolean(position), date: new Date().toISOString() };
    if (op !== "statut") {
      const serie = donnees ? donnees.numeroSerie : saisie;
      noterRecent({ op, serie: serie || "Code scanné", issue: refus ? "refus" : donnees.alerte ? "alerte" : "ok", date: resultat.date });
    }
    etat.resultat = resultat;
    vibrer(refus || (donnees && donnees.alerte) ? [80, 60, 80] : 60);
    aller("#/resultat");
  }

  function ouvrirErreur({ titre, texte }) {
    const f = document.createElement("div");
    f.innerHTML = `<div class="voile"></div><section class="feuille erreur-feuille" role="alertdialog" aria-label="${echapper(titre)}">
      <div class="poignee"></div><div class="icone">${icone("attention", 28)}</div>
      <h2>${echapper(titre)}</h2><p class="aide">${echapper(texte)}</p>
      <div class="actions-bas"><button class="bouton" data-action="reprendre">Reprendre la photo</button>
      <button class="bouton discret" data-action="saisie-erreur">Saisir le numéro de série</button></div></section>`;
    document.body.appendChild(f);
    f.querySelector('[data-action="reprendre"]').addEventListener("click", () => f.remove());
    f.querySelector('[data-action="saisie-erreur"]').addEventListener("click", () => { f.remove(); ouvrirSaisie(); });
    f.querySelector('[data-action="reprendre"]').focus();
  }

  function ouvrirSaisie() {
    const f = document.createElement("div");
    f.innerHTML = `<div class="voile"></div><form class="feuille" aria-label="Saisie du numéro de série" novalidate>
      <div class="poignee"></div><h2>Numéro de série</h2><p class="aide">Le numéro de série est écrit sous le code, après <strong>(21)</strong>. Recopiez ce qui suit, sans les parenthèses.</p>
      <label class="champ"><span class="visuel-seulement">Numéro de série</span><div class="saisie"><input name="serie" autocomplete="off" autocapitalize="characters" spellcheck="false" inputmode="text" required></div></label>
      <div class="actions-bas" style="display:grid;gap:10px"><button class="bouton" type="submit">${op === "statut" ? "Vérifier" : "Valider"}</button>
      <button class="bouton discret" type="button" data-action="annuler">Annuler</button></div></form>`;
    document.body.appendChild(f);
    const form = f.querySelector("form");
    form.serie.focus();
    f.querySelector(".voile").addEventListener("click", () => f.remove());
    f.querySelector('[data-action="annuler"]').addEventListener("click", () => f.remove());
    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const serie = form.serie.value.trim();
      if (!serie) { form.serie.focus(); return; }
      f.remove(); envoyer({ serie });
    });
  }

  racine.querySelector('[data-action="retour"]').addEventListener("click", () => aller("#/"));
  racine.querySelector('[data-action="saisie"]').addEventListener("click", ouvrirSaisie);
  racine.querySelector('[data-action="galerie"]').addEventListener("click", () => {
    const champ = document.getElementById("fichier");
    champ.removeAttribute("capture"); champ.click();
  });
  const champ = document.getElementById("fichier");
  champ.addEventListener("change", () => { const fichier = champ.files[0]; champ.value = ""; if (fichier) envoyer({ fichier }); });

  racine.querySelector('[data-action="capturer"]').addEventListener("click", () => {
    if (flux && video.videoWidth) {
      const toile = document.createElement("canvas");
      toile.width = video.videoWidth; toile.height = video.videoHeight;
      toile.getContext("2d").drawImage(video, 0, 0);
      toile.toBlob((blob) => blob && envoyer({ fichier: new File([blob], "code.jpg", { type: "image/jpeg" }) }), "image/jpeg", 0.92);
    } else {
      // Pas de flux vidéo (accès refusé ou page non sécurisée): l'appareil photo du téléphone prend le relais
      champ.setAttribute("capture", "environment"); champ.click();
    }
  });
  racine.querySelector('[data-action="lampe"]')?.addEventListener("click", async (ev) => {
    lampe = !lampe;
    try { await flux.getVideoTracks()[0].applyConstraints({ advanced: [{ torch: lampe }] }); ev.currentTarget.setAttribute("aria-pressed", String(lampe)); } catch { lampe = !lampe; }
  });
}

// Une photo prise avec l'appareil du telephone peut depasser la limite du serveur (5 Mo): on la reduit avant l'envoi.
// Une photo deja assez legere part telle quelle, sans perte. Le cote le plus long garde 2560 pixels: un code reste lisible.
const POIDS_MAX_PHOTO = 4 * 1024 * 1024;
const COTE_MAX_PHOTO = 2560;
async function reduireImage(fichier) {
  if (!fichier || fichier.size <= POIDS_MAX_PHOTO) return fichier;
  try {
    const image = await createImageBitmap(fichier, { imageOrientation: "from-image" });
    const echelle = Math.min(1, COTE_MAX_PHOTO / Math.max(image.width, image.height));
    const toile = document.createElement("canvas");
    toile.width = Math.round(image.width * echelle); toile.height = Math.round(image.height * echelle);
    toile.getContext("2d").drawImage(image, 0, 0, toile.width, toile.height);
    image.close?.();
    for (let qualite = 0.92; qualite > 0.5; qualite -= 0.12) {
      const blob = await new Promise((r) => toile.toBlob(r, "image/jpeg", qualite));
      if (blob && blob.size <= POIDS_MAX_PHOTO) return new File([blob], "code.jpg", { type: "image/jpeg" });
    }
  } catch { /* navigateur sans createImageBitmap, ou image illisible: on envoie l'originale */ }
  return fichier;
}

/* ------------------------------------------------------------------ Résultat */

function ligne(libelle, valeur, classe = "") { return `<div class="ligne"><dt>${libelle}</dt><dd class="${classe}">${valeur}</dd></div>`; }

function vueResultat() {
  const r = etat.resultat;
  if (r.op === "statut") { vueStatut(r); return; }
  const o = OPERATIONS[r.op];
  let genre, titre, sous, serie = r.donnees ? r.donnees.numeroSerie : r.serie;
  if (r.refus !== null && !r.donnees) {
    genre = "refus"; titre = "Dispensation non validée";
    sous = "Cet identifiant est déjà désactivé. Une réutilisation est possible : une alerte est soumise à vérification.";
  } else if (r.donnees.alerte) {
    genre = "alerte"; titre = o.alerte;
    const rupture = r.donnees.typeAnomalie === "ruptureSequence" || (!r.donnees.typeAnomalie && r.op === "dispensation");
    sous = !rupture
      ? "Cet identifiant était déjà désactivé. L'événement est gardé avec une alerte à vérifier."
      : r.op === "dispensation"
        ? "Aucune réception par cette officine dans l'historique de l'unité. À faire vérifier."
        : "Aucune expédition de cette unité dans l'historique : l'événement est gardé avec une alerte à vérifier.";
  } else {
    genre = "ok"; titre = o.succes; sous = "L'unité est enregistrée dans l'historique.";
  }
  const symbole = genre === "ok" ? icone("coche", 46) : genre === "alerte" ? icone("attention", 46) : icone("croix", 46);
  const lignes = [];
  if (serie) lignes.push(ligne("Unité", echapper(serie), "serie"));
  lignes.push(ligne("Opération", o.titre));
  lignes.push(ligne("Date", dateLongue(r.donnees ? r.donnees.dateHeure : r.date)));
  const avecPosition = r.donnees ? r.donnees.latitude != null : r.position;
  lignes.push(ligne("Position", avecPosition ? "Enregistrée" : "Non transmise"));
  if (r.donnees && r.donnees.methodeLecture) lignes.push(ligne("Lecture", LECTURES[r.donnees.methodeLecture] || echapper(r.donnees.methodeLecture)));
  racine.innerHTML = `<main class="resultat ${genre}">
    <div class="haut"><div class="sceau" aria-hidden="true">${symbole}</div>
      <h1 role="status">${titre}</h1><p class="sous-titre">${sous}</p></div>
    <div class="corps"><dl class="fiche">${lignes.join("")}</dl>
    ${genre !== "ok" ? `<p class="avis">${AVIS}</p>` : ""}
    <div class="bas"><button class="bouton" data-action="encore">${icone("scan", 22)}Scanner une autre unité</button>
    <button class="bouton discret" data-action="fin">Terminer</button></div></div></main>`;
  racine.querySelector('[data-action="encore"]').addEventListener("click", () => aller(`#/scan/${r.op}`));
  racine.querySelector('[data-action="fin"]').addEventListener("click", () => aller("#/"));
}

function vueStatut(r) {
  const s = r.donnees;
  const active = s.statut === "active";
  const anomalie = s.anomalie;
  const genre = anomalie ? "alerte" : "ok";
  const symbole = anomalie ? icone("attention", 46) : icone("verifier", 46);
  const dernier = s.dernierEvenement;
  const typeOp = { reception: "Réception", expedition: "Expédition", dispensation: "Dispensation" };
  const lignes = [
    ligne("Unité", echapper(s.numeroSerie), "serie"),
    ligne("Identifiant", active ? '<span class="etat vert">Actif</span>' : '<span class="etat gris">Désactivé</span>'),
    dernier ? ligne("Dernier mouvement", `${typeOp[dernier.typeOperation] || dernier.typeOperation}<br><small style="font-weight:500;color:var(--encre-douce)">${dateLongue(dernier.dateHeure)}</small>`)
      : ligne("Dernier mouvement", "Aucun"),
  ];
  if (dernier && dernier.latitude != null) {
    lignes.push(ligne("Lieu", `<a href="https://www.openstreetmap.org/?mlat=${dernier.latitude}&mlon=${dernier.longitude}#map=15/${dernier.latitude}/${dernier.longitude}" target="_blank" rel="noopener" style="color:var(--pin)">Voir sur la carte</a>`));
  }
  if (s.methodeLecture) lignes.push(ligne("Lecture", LECTURES[s.methodeLecture] || echapper(s.methodeLecture)));
  if (anomalie) lignes.push(ligne("Anomalie", `<span class="etat ambre">${ANOMALIES[anomalie.typeAnomalie] || anomalie.typeAnomalie}</span><br><small style="font-weight:500;color:var(--encre-douce)">${anomalie.statut === "a_verifier" ? "À vérifier" : echapper(anomalie.statut)} · ${dateLongue(anomalie.dateDetection)}</small>`));
  racine.innerHTML = `<main class="resultat ${genre}">
    <div class="haut"><div class="sceau" aria-hidden="true">${symbole}</div>
    <h1 role="status">${active ? "Identifiant actif" : "Identifiant désactivé"}</h1>
    <p class="sous-titre">${active ? "L'unité peut encore circuler dans le circuit." : "L'unité a été remise à un patient : son identifiant ne doit plus servir."}</p></div>
    <div class="corps"><dl class="fiche">${lignes.join("")}</dl>
    ${anomalie ? `<p class="avis">${AVIS}</p>` : ""}
    <div class="bas"><button class="bouton" data-action="encore">${icone("scan", 22)}Vérifier une autre unité</button>
    <button class="bouton discret" data-action="fin">Terminer</button></div></div></main>`;
  racine.querySelector('[data-action="encore"]').addEventListener("click", () => aller("#/scan/statut"));
  racine.querySelector('[data-action="fin"]').addEventListener("click", () => aller("#/"));
}

/* ------------------------------------------------------------------ Pages de gestion */

// Page secondaire: bouton retour, titre, puis le contenu
function sousPage(titre, corps, retour = "#/") {
  racine.innerHTML = `<main class="page">
    <header class="sous-entete"><button class="retour" data-aller="${retour}" aria-label="Retour">${icone("retour")}</button><h1>${titre}</h1></header>
    ${corps}</main>${barre("accueil")}`;
  brancherBarre();
}

// Champ de formulaire avec message d'erreur propre à ce champ
function champ(nom, libelle, o = {}) {
  const { type = "text", aide = "", valeur = "", mdp = false, liste = "", ...attrs } = o;
  const attributs = Object.entries(attrs).map(([k, v]) => `${k}="${echapper(v)}"`).join(" ");
  const saisie = type === "textarea"
    ? `<textarea name="${nom}" rows="3" ${attributs}>${echapper(valeur)}</textarea>`
    : `<input name="${nom}" type="${type}" value="${echapper(valeur)}" ${liste ? `list="${liste}"` : ""} ${attributs}>`;
  return `<label class="champ"><span>${libelle}</span>
    <div class="saisie">${saisie}${mdp ? `<button type="button" class="oeil" data-action="oeil" aria-label="Afficher le mot de passe">${icone("oeil")}</button>` : ""}</div>
    ${aide ? `<small class="aide-champ">${aide}</small>` : ""}
    <small class="erreur-champ" data-erreur="${nom}"></small></label>`;
}

const ALPHABET_MDP = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
function genererMdp() {
  const octets = crypto.getRandomValues(new Uint8Array(10));
  return Array.from(octets, (o) => ALPHABET_MDP[o % ALPHABET_MDP.length]).join("");
}
const boutonGenerer = '<button type="button" class="lien" data-action="generer">Générer un mot de passe</button>';

function brancherChamps(form) {
  form.querySelectorAll('[data-action="oeil"]').forEach((b) => b.addEventListener("click", () => {
    const entree = b.closest(".saisie").querySelector("input");
    const visible = entree.type === "text";
    entree.type = visible ? "password" : "text";
    b.innerHTML = icone(visible ? "oeil" : "oeilBarre");
    b.setAttribute("aria-label", visible ? "Afficher le mot de passe" : "Masquer le mot de passe");
  }));
  form.querySelector('[data-action="generer"]')?.addEventListener("click", () => {
    const m = genererMdp();
    for (const n of ["motDePasse", "nouveauMotDePasse", "confirmation"]) {
      const entree = form.elements[n];
      if (!entree) continue;
      entree.value = m; entree.type = "text"; effacerErreur(form, n);
      const oeil = entree.closest(".saisie").querySelector('[data-action="oeil"]');
      if (oeil) { oeil.innerHTML = icone("oeilBarre"); oeil.setAttribute("aria-label", "Masquer le mot de passe"); }
    }
  });
  form.addEventListener("input", (ev) => { if (ev.target.name) effacerErreur(form, ev.target.name); });
}

function effacerErreur(form, nom) {
  const zone = form.querySelector(`[data-erreur="${nom}"]`);
  if (zone) zone.textContent = "";
  form.elements[nom]?.closest?.(".saisie")?.classList.remove("invalide");
}

// regles: [nom, fonction(valeur) -> message d'erreur ou ""]
function valider(form, regles) {
  let premier = null;
  for (const [nom, test] of regles) {
    const entree = form.elements[nom];
    if (!entree) continue;
    const message = test(entree.value.trim());
    const zone = form.querySelector(`[data-erreur="${nom}"]`);
    if (zone) zone.textContent = message;
    entree.closest(".saisie")?.classList.toggle("invalide", Boolean(message));
    if (message && !premier) premier = entree;
  }
  premier?.focus();
  return !premier;
}

const minimum = (n, message) => (v) => (v.length >= n ? "" : message);
const requis = (message) => (v) => (v ? "" : message);

const regleNom = minimum(2, "Saisissez au moins 2 caractères.");
const regleFonction = minimum(2, "Saisissez au moins 2 caractères.");
const regleIdentifiant = minimum(3, "L'identifiant compte au moins 3 caractères.");
const regleMdp = minimum(8, "Le mot de passe compte au moins 8 caractères.");
const regleCourriel = (v) => (/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(v) ? "" : "Saisissez une adresse e-mail valide.");
const champCourriel = (valeur = "", aide = "Sert à récupérer le mot de passe en cas d'oubli") =>
  champ("email", "Adresse e-mail", { type: "email", valeur, inputmode: "email", autocomplete: "email", autocapitalize: "none", spellcheck: "false", maxlength: 254, aide });

function texteGestion(e) {
  const d = e.detail || "";
  if (e.statut === 0) return "Le serveur est injoignable. Vérifiez votre connexion et réessayez.";
  if (/adresse e-mail/i.test(d)) return /identifiant|reference/i.test(d) ? "Cette référence, cet identifiant ou cette adresse e-mail est déjà utilisé." : "Cette adresse e-mail est déjà utilisée.";
  if (/lien invalide/i.test(d)) return "Ce lien n'est plus valable (expiré ou déjà utilisé). Refaites une demande.";
  if (/ne s'inscrit pas/i.test(d)) return "Un service régional ne s'inscrit pas lui-même : son compte responsable est créé par la Pharmacie nationale.";
  if (/aucune correspondance/i.test(d)) return "Cette référence d'autorisation est introuvable. Vérifiez-la, ou contactez l'ARP.";
  if (/structure est deja inscrite/i.test(d)) return "Une structure est déjà inscrite avec cette référence.";
  if (/identifiant de connexion est deja utilise|identifiant deja utilise/i.test(d)) return "Cet identifiant de connexion est déjà utilisé. Choisissez-en un autre.";
  if (/inscription impossible|compte impossible/i.test(d)) return "Cette référence ou cet identifiant est déjà utilisé.";
  if (/gtin invalide/i.test(d)) return "GTIN invalide : 14 chiffres avec une clé de contrôle correcte.";
  if (/gtin/i.test(d)) return "Un produit est déjà enregistré avec ce GTIN.";
  if (/deja serialise/i.test(d)) return "Ce lot est déjà sérialisé pour ce produit.";
  if (/produit introuvable/i.test(d)) return "Produit introuvable. Enregistrez-le d'abord.";
  if (/n'appartient pas/i.test(d)) return "Ce produit n'appartient pas à votre structure.";
  if (/peremption/i.test(d)) return "La date de péremption doit être dans le futur.";
  if (/sr introuvable/i.test(d)) return "Ce service régional est introuvable parmi ceux de votre pharmacie nationale.";
  if (/sr dispose deja/i.test(d)) return "Ce service régional dispose déjà d'un compte responsable.";
  if (/actuel incorrect/i.test(d)) return "Le mot de passe actuel est incorrect.";
  if (/different de l'actuel/i.test(d)) return "Choisissez un mot de passe différent de l'actuel.";
  if (e.statut === 403) return "Votre compte n'est pas autorisé à effectuer cette action.";
  if (d === "validation" || e.statut === 422) return "Vérifiez les champs saisis.";
  return "L'opération n'a pas abouti. Réessayez.";
}

// Envoie le formulaire: bouton occupé, erreur du serveur affichée en haut du formulaire
async function soumettre(form, libelleOccupe, action) {
  const zone = form.querySelector("[data-zone-erreur]"), bouton = form.querySelector('button[type="submit"]');
  const texte = bouton.innerHTML;
  bouton.disabled = true; bouton.textContent = libelleOccupe; zone.innerHTML = "";
  try {
    await action();
  } catch (e) {
    if (e.statut === 401) { fermerSession(); return; }
    zone.innerHTML = blocErreur(texteGestion(e));
    zone.scrollIntoView({ block: "center", behavior: "smooth" });
    bouton.disabled = false; bouton.innerHTML = texte;
  }
}
const zoneErreur = '<div data-zone-erreur role="alert"></div>';

// Écran de confirmation, dans le même style que le résultat d'un scan
function afficherSucces({ titre, sous, lignes = [], extra = "", boutons = [] }) {
  racine.innerHTML = `<main class="resultat ok">
    <div class="haut"><div class="sceau" aria-hidden="true">${icone("coche", 46)}</div>
      <h1 role="status">${titre}</h1><p class="sous-titre">${sous}</p></div>
    <div class="corps">${lignes.length ? `<dl class="fiche">${lignes.map(([l, v, c]) => ligne(l, v, c || "")).join("")}</dl>` : ""}
    ${extra}
    <div class="bas">${boutons.map((b, i) => `<${b.href ? `a href="${b.href}" download="${echapper(b.telecharger)}"` : "button"} class="bouton ${b.discret ? "discret" : ""}" data-i="${i}">${b.icone ? icone(b.icone, 22) : ""}${b.texte}</${b.href ? "a" : "button"}>`).join("")}</div></div></main>`;
  boutons.forEach((b, i) => { if (b.clic) racine.querySelector(`[data-i="${i}"]`).addEventListener("click", b.clic); });
}

/* ---------- Inscription d'une structure (fiche 1) ---------- */

const TYPES_INSCRIPTION = [
  ["fabricant", "Fabricant", "Laboratoire qui sérialise ses produits"],
  ["grossisteRepartiteur", "Grossiste répartiteur", "Reçoit et expédie les lots"],
  ["officine", "Officine", "Reçoit et dispense les unités"],
  ["PNA", "Pharmacie nationale", "Suit le circuit et crée les comptes des services régionaux"],
];
let identifiantInitial = "";

function vueInscription(etape = 1, saisi = {}) {
  const progression = `<div class="progression" role="img" aria-label="Étape ${etape} sur 2"><i class="${etape >= 1 ? "fait" : ""}"></i><i class="${etape >= 2 ? "fait" : ""}"></i></div>`;
  if (etape === 1) {
    racine.innerHTML = `<main class="page page-simple">
      <header class="sous-entete"><button class="retour" data-aller="#/connexion" aria-label="Retour à la connexion">${icone("retour")}</button><h1>Inscrire ma structure</h1></header>
      ${progression}<p class="etape-titre">Étape 1 sur 2 · Votre structure</p>
      <form id="formulaire" novalidate>
        <div class="champ"><span id="lib-type" class="libelle-groupe">Type de structure</span>
          <div class="choix-types" role="radiogroup" aria-labelledby="lib-type">
            ${TYPES_INSCRIPTION.map(([v, t, d]) => `<button type="button" class="choix-type" role="radio" aria-checked="${saisi.type === v}" data-type="${v}">
              <span class="coche-radio"></span><span class="texte"><strong>${t}</strong><small>${d}</small></span></button>`).join("")}
          </div>
          <small class="aide-champ">Un service régional ne s'inscrit pas : son compte est créé par la Pharmacie nationale.</small>
          <small class="erreur-champ" data-erreur="type"></small></div>
        ${champ("nom", "Nom de la structure", { valeur: saisi.nom || "", autocomplete: "organization", maxlength: 200 })}
        ${champ("localisation", "Localisation", { valeur: saisi.localisation || "", aide: "Ville ou adresse de la structure", maxlength: 200 })}
        ${champ("referenceAutorisation", "Référence d'autorisation", { valeur: saisi.referenceAutorisation || "", aide: "Telle qu'elle figure sur l'autorisation de votre structure", autocapitalize: "characters", spellcheck: "false", maxlength: 100 })}
        <button class="bouton" type="submit">Continuer</button>
      </form></main>`;
    brancherBarre();
    const form = document.getElementById("formulaire");
    let type = saisi.type || "";
    form.querySelectorAll(".choix-type").forEach((b) => b.addEventListener("click", () => {
      type = b.dataset.type;
      form.querySelectorAll(".choix-type").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
      form.querySelector('[data-erreur="type"]').textContent = "";
    }));
    brancherChamps(form);
    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const ok = valider(form, [
        ["nom", minimum(2, "Saisissez le nom de la structure.")],
        ["localisation", minimum(2, "Saisissez la localisation.")],
        ["referenceAutorisation", requis("Saisissez la référence d'autorisation.")],
      ]);
      if (!type) { form.querySelector('[data-erreur="type"]').textContent = "Choisissez le type de votre structure."; form.querySelector(".choix-type").focus(); return; }
      if (!ok) return;
      vueInscription(2, { ...saisi, type, nom: form.nom.value.trim(), localisation: form.localisation.value.trim(), referenceAutorisation: form.referenceAutorisation.value.trim() });
    });
    return;
  }
  racine.innerHTML = `<main class="page page-simple">
    <header class="sous-entete"><button class="retour" data-action="precedent" aria-label="Étape précédente">${icone("retour")}</button><h1>Inscrire ma structure</h1></header>
    ${progression}<p class="etape-titre">Étape 2 sur 2 · Le responsable du compte</p>
    <div class="recap">${icone("batiment", 22)}<span><strong>${echapper(saisi.nom)}</strong>${TYPES_STRUCTURE[saisi.type]} · ${echapper(saisi.localisation)}</span></div>
    <form id="formulaire" novalidate>
      ${zoneErreur}
      ${champ("responsableNom", "Nom et prénom", { valeur: saisi.responsableNom || "", autocomplete: "name", maxlength: 200 })}
      ${champ("fonction", "Fonction", { valeur: saisi.fonction || "", aide: "Par exemple : pharmacien responsable", maxlength: 100 })}
      ${champ("identifiantConnexion", "Identifiant de connexion", { valeur: saisi.identifiantConnexion || "", autocomplete: "username", autocapitalize: "none", spellcheck: "false", maxlength: 100 })}
      ${champCourriel(saisi.email || "")}
      ${champ("motDePasse", "Mot de passe", { type: "password", mdp: true, autocomplete: "new-password", aide: "8 caractères au moins", maxlength: 128 })}
      <button class="bouton" type="submit">Créer le compte</button>
    </form></main>`;
  const form = document.getElementById("formulaire");
  racine.querySelector('[data-action="precedent"]').addEventListener("click", () => vueInscription(1, { ...saisi, responsableNom: form.responsableNom.value.trim(), fonction: form.fonction.value.trim(), identifiantConnexion: form.identifiantConnexion.value.trim(), email: form.email.value.trim() }));
  brancherChamps(form);
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (!valider(form, [["responsableNom", regleNom], ["fonction", regleFonction], ["identifiantConnexion", regleIdentifiant], ["email", regleCourriel], ["motDePasse", (v) => (form.motDePasse.value.length >= 8 ? "" : "Le mot de passe compte au moins 8 caractères.")]])) return;
    const actuel = { ...saisi, responsableNom: form.responsableNom.value.trim(), fonction: form.fonction.value.trim(), identifiantConnexion: form.identifiantConnexion.value.trim(), email: form.email.value.trim() };
    soumettre(form, "Création du compte…", async () => {
      await api("/structures/inscription", { methode: "POST", json: {
        structure: { nom: saisi.nom, type: saisi.type, localisation: saisi.localisation, referenceAutorisation: saisi.referenceAutorisation },
        responsable: { nom: actuel.responsableNom, fonction: actuel.fonction, identifiantConnexion: actuel.identifiantConnexion, email: actuel.email, motDePasse: form.motDePasse.value },
      } });
      identifiantInitial = actuel.identifiantConnexion;
      afficherSucces({
        titre: "Compte créé",
        sous: saisi.type === "PNA"
          ? "Vous pouvez maintenant créer les comptes responsables des services régionaux."
          : "Votre structure est inscrite. Connectez-vous pour commencer.",
        lignes: [["Structure", echapper(saisi.nom)], ["Type", TYPES_STRUCTURE[saisi.type]], ["Identifiant", echapper(actuel.identifiantConnexion), "serie"]],
        boutons: [{ texte: "Se connecter", clic: () => aller("#/connexion") }],
      });
    });
  });
}

/* ---------- Compte d'un employé (fiche 2) ---------- */

function vueEquipe() {
  sousPage("Ajouter un employé", `
    <p class="intro">L'employé se connectera avec l'identifiant et le mot de passe initial que vous lui donnez.</p>
    <form id="formulaire" novalidate>${zoneErreur}
      ${champ("nom", "Nom et prénom", { maxlength: 200 })}
      ${champ("fonction", "Fonction", { aide: "Par exemple : préparateur en pharmacie", maxlength: 100 })}
      ${champ("identifiantConnexion", "Identifiant de connexion", { autocapitalize: "none", spellcheck: "false", autocomplete: "off", maxlength: 100 })}
      ${champCourriel("", "Adresse personnelle de cette personne : elle recevra le lien en cas de mot de passe oublié")}
      ${champ("motDePasse", "Mot de passe initial", { type: "password", mdp: true, autocomplete: "new-password", aide: "8 caractères au moins", maxlength: 128 })}
      ${boutonGenerer}
      <button class="bouton" type="submit">Créer le compte</button>
    </form>`);
  const form = document.getElementById("formulaire");
  brancherChamps(form);
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (!valider(form, [["nom", regleNom], ["fonction", regleFonction], ["identifiantConnexion", regleIdentifiant], ["email", regleCourriel], ["motDePasse", () => (form.motDePasse.value.length >= 8 ? "" : "Le mot de passe compte au moins 8 caractères.")]])) return;
    soumettre(form, "Création du compte…", async () => {
      const mdp = form.motDePasse.value;
      const e = await api("/employes", { methode: "POST", json: { nom: form.nom.value.trim(), fonction: form.fonction.value.trim(), identifiantConnexion: form.identifiantConnexion.value.trim(), email: form.email.value.trim(), motDePasse: mdp } });
      afficherSucces({
        titre: "Compte employé créé",
        sous: "Transmettez-lui son identifiant et son mot de passe initial.",
        lignes: [["Employé", echapper(e.nom)], ["Fonction", echapper(e.fonction)], ["Identifiant", echapper(e.identifiantConnexion), "serie"], ["Mot de passe initial", echapper(mdp), "serie"]],
        boutons: [{ texte: "Ajouter un autre employé", icone: "plus", clic: () => aller("#/equipe") }, { texte: "Terminer", discret: true, clic: () => aller("#/") }],
      });
    });
  });
}

/* ---------- Produits (fiche 3) ---------- */

function vueProduits() {
  sousPage("Produits", `
    <button class="bouton" data-aller="#/produits/nouveau">${icone("plus", 22)}Nouveau produit</button>
    <label class="champ recherche"><span class="visuel-seulement">Rechercher un produit</span>
      <div class="saisie">${icone("loupe", 20)}<input id="recherche" type="search" placeholder="Nom du produit ou GTIN" autocomplete="off" spellcheck="false" maxlength="100"></div></label>
    <div id="resultats" aria-live="polite"></div>`);
  const zone = document.getElementById("resultats"), entree = document.getElementById("recherche");
  const invite = '<div class="vide"><strong>Retrouvez un de vos produits</strong>Saisissez au moins 2 lettres de son nom, ou son GTIN, puis appuyez dessus pour sérialiser un lot.</div>';
  zone.innerHTML = invite;
  let minuteur = null, numero = 0;
  entree.addEventListener("input", () => {
    clearTimeout(minuteur);
    const q = entree.value.trim();
    if (q.length < 2) { numero++; zone.innerHTML = invite; return; }
    minuteur = setTimeout(async () => {
      const mien = ++numero;
      zone.innerHTML = '<div class="vide">Recherche…</div>';
      try {
        const liste = await api(`/produits?q=${encodeURIComponent(q)}`);
        if (mien !== numero) return;
        if (!liste.length) { zone.innerHTML = '<div class="vide"><strong>Aucun produit trouvé</strong>Vérifiez l\'orthographe, ou enregistrez un nouveau produit.</div>'; return; }
        zone.innerHTML = `<div class="liste-produits">${liste.map((p) => `<button class="recent produit" data-id="${echapper(p.id)}">
          <span class="pastille ok">${icone("produit", 20)}</span>
          <span class="texte"><strong>${echapper(p.nom)}</strong><small>${echapper(p.formePharmaceutique)} · ${echapper(p.conditionnement)}</small><small>${p.gtin ? `GTIN ${echapper(p.gtin)}` : "Sans GTIN"}</small></span>
          <span class="fleche">${icone("fleche", 18)}</span></button>`).join("")}</div>`;
        zone.querySelectorAll("[data-id]").forEach((b) => b.addEventListener("click", () => {
          etat.produit = liste.find((p) => p.id === b.dataset.id); aller("#/lot");
        }));
      } catch (e) {
        if (mien !== numero) return;
        if (e.statut === 401) { fermerSession(); return; }
        zone.innerHTML = blocErreur(texteGestion(e));
      }
    }, 300);
  });
}

const FORMES = ["Comprimé", "Gélule", "Sirop", "Solution injectable", "Suspension buvable", "Crème", "Pommade", "Collyre", "Suppositoire", "Poudre pour solution buvable"];

function gtinValide(g) {
  if (!/^\d{14}$/.test(g)) return false;
  const somme = [...g.slice(0, 13)].reverse().reduce((s, c, i) => s + Number(c) * (i % 2 === 0 ? 3 : 1), 0);
  return (10 - (somme % 10)) % 10 === Number(g[13]);
}

function vueProduitNouveau() {
  sousPage("Nouveau produit", `
    <form id="formulaire" novalidate>${zoneErreur}
      ${champ("nom", "Nom du produit", { maxlength: 200 })}
      ${champ("formePharmaceutique", "Forme pharmaceutique", { liste: "formes", autocomplete: "off", maxlength: 100 })}
      <datalist id="formes">${FORMES.map((f) => `<option value="${f}">`).join("")}</datalist>
      ${champ("composition", "Composition", { type: "textarea", maxlength: 500, aide: "Principe actif et dosage" })}
      ${champ("conditionnement", "Conditionnement", { maxlength: 200, aide: "Par exemple : boîte de 20 comprimés" })}
      ${champ("gtin", "GTIN (facultatif)", { inputmode: "numeric", maxlength: 14, autocomplete: "off", aide: "14 chiffres. Sans GTIN, le produit est identifié par un code interne." })}
      <button class="bouton" type="submit">Enregistrer le produit</button>
    </form>`, "#/produits");
  const form = document.getElementById("formulaire");
  brancherChamps(form);
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (!valider(form, [
      ["nom", regleNom], ["formePharmaceutique", minimum(2, "Saisissez la forme pharmaceutique.")],
      ["composition", minimum(2, "Saisissez la composition.")], ["conditionnement", minimum(2, "Saisissez le conditionnement.")],
      ["gtin", (v) => (!v || gtinValide(v) ? "" : "GTIN invalide : 14 chiffres avec une clé de contrôle correcte.")],
    ])) return;
    soumettre(form, "Enregistrement…", async () => {
      const v = (n) => form[n].value.trim();
      const p = await api("/produits", { methode: "POST", json: { nom: v("nom"), formePharmaceutique: v("formePharmaceutique"), composition: v("composition"), conditionnement: v("conditionnement"), gtin: v("gtin") || null } });
      afficherSucces({
        titre: "Produit enregistré",
        sous: "Vous pouvez maintenant sérialiser un lot de ce produit.",
        lignes: [["Produit", echapper(p.nom)], ["Forme", echapper(p.formePharmaceutique)], ["Conditionnement", echapper(p.conditionnement)], ["GTIN", p.gtin ? echapper(p.gtin) : "Code interne", "serie"]],
        boutons: [
          { texte: "Sérialiser un lot", icone: "grille", clic: () => { etat.produit = p; aller("#/lot"); } },
          { texte: "Terminer", discret: true, clic: () => aller("#/") },
        ],
      });
    });
  });
}

/* ---------- Sérialisation d'un lot (fiche 4) ---------- */

// Lit le premier code image de l'archive ZIP, pour montrer un code à scanner
async function premierCode(blob) {
  try {
    const entete = new DataView(await blob.slice(0, 30).arrayBuffer());
    if (entete.getUint32(0, true) !== 0x04034b50) return null;
    const methode = entete.getUint16(8, true), taille = entete.getUint32(18, true);
    const longNom = entete.getUint16(26, true), longExtra = entete.getUint16(28, true);
    if (!taille || (entete.getUint16(6, true) & 8)) return null;
    const debut = 30 + longNom + longExtra;
    const nom = await blob.slice(30, 30 + longNom).text();
    let donnees = blob.slice(debut, debut + taille);
    if (methode === 8) donnees = await new Response(donnees.stream().pipeThrough(new DecompressionStream("deflate-raw"))).blob();
    else if (methode !== 0) return null;
    return { serie: nom.replace(/\.png$/i, ""), url: URL.createObjectURL(new Blob([donnees], { type: "image/png" })) };
  } catch { return null; }
}

function vueLot() {
  const p = etat.produit;
  if (!p) { aller("#/produits"); return; }
  const demain = new Date(Date.now() + 86400000), min = `${demain.getFullYear()}-${String(demain.getMonth() + 1).padStart(2, "0")}-${String(demain.getDate()).padStart(2, "0")}`;
  sousPage("Sérialiser un lot", `
    <div class="recap">${icone("produit", 22)}<span><strong>${echapper(p.nom)}</strong>${echapper(p.formePharmaceutique)} · ${echapper(p.conditionnement)}</span>
      <button class="lien" data-aller="#/produits">Changer</button></div>
    <form id="formulaire" novalidate>${zoneErreur}
      ${champ("numeroLot", "Numéro de lot", { maxlength: 20, autocapitalize: "characters", autocomplete: "off", spellcheck: "false", aide: "20 caractères au maximum, sans parenthèses" })}
      ${champ("datePeremption", "Date de péremption", { type: "date", min })}
      ${champ("quantite", "Nombre d'unités", { type: "number", inputmode: "numeric", min: "1", max: "10000", step: "1", aide: "De 1 à 10 000 unités par lot" })}
      <button class="bouton" type="submit">${icone("grille", 22)}Générer les codes</button>
    </form>`, "#/produits");
  const form = document.getElementById("formulaire");
  brancherChamps(form);
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (!valider(form, [
      ["numeroLot", (v) => (!v ? "Saisissez le numéro de lot." : v.length > 20 ? "20 caractères au maximum." : /[()]/.test(v) ? "Les parenthèses ne sont pas admises." : "")],
      ["datePeremption", (v) => (!v ? "Choisissez la date de péremption." : v < min ? "La date doit être dans le futur." : "")],
      ["quantite", (v) => (/^\d+$/.test(v) && Number(v) >= 1 && Number(v) <= 10000 ? "" : "Saisissez un nombre entre 1 et 10 000.")],
    ])) return;
    const chargement = document.createElement("div");
    chargement.className = "chargement"; chargement.setAttribute("role", "status");
    chargement.innerHTML = '<div><div class="anneau"></div><strong>Génération des codes…</strong></div>';
    soumettre(form, "Génération…", async () => {
      document.body.appendChild(chargement);
      try {
        const lot = form.numeroLot.value.trim(), peremption = form.datePeremption.value, quantite = Number(form.quantite.value);
        const reponse = await requete("/lots/serialisation", { methode: "POST", json: { produit_id: p.id, numeroLot: lot, datePeremption: peremption, quantite } });
        const archive = await reponse.blob();
        const code = await premierCode(archive);
        const lien = URL.createObjectURL(archive);
        afficherSucces({
          titre: "Lot sérialisé",
          sous: `${quantite} ${quantite > 1 ? "codes ont été générés" : "code a été généré"}. Téléchargez l'archive pour les imprimer.`,
          lignes: [["Produit", echapper(p.nom)], ["Lot", echapper(lot), "serie"], ["Péremption", new Date(`${peremption}T12:00:00`).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })], ["Unités", String(quantite)]],
          extra: code ? `<figure class="apercu-code"><img src="${code.url}" alt="Premier code DataMatrix du lot"><figcaption>Premier code du lot<br><span class="serie">${echapper(code.serie)}</span></figcaption></figure>` : "",
          boutons: [
            { texte: "Télécharger les codes (ZIP)", icone: "telecharger", href: lien, telecharger: `codes_${lot}.zip` },
            { texte: "Sérialiser un autre lot", discret: true, clic: () => aller("#/lot") },
            { texte: "Terminer", discret: true, clic: () => aller("#/") },
          ],
        });
      } finally { chargement.remove(); }
    });
  });
}

/* ---------- Services régionaux (fiche 4 de la PNA) ---------- */

async function vueSR() {
  sousPage("Services régionaux", '<p class="intro">Créez le compte du responsable de chaque service régional.</p><div id="liste" aria-live="polite"><div class="vide">Chargement…</div></div>');
  const zone = document.getElementById("liste");
  try {
    const liste = await api("/sr");
    if (!liste.length) { zone.innerHTML = '<div class="vide"><strong>Aucun service régional</strong>Aucun service régional n\'est rattaché à votre pharmacie nationale.</div>'; return; }
    zone.innerHTML = `<div class="liste-produits">${liste.map((s) => {
      const interieur = `<span class="pastille ${s.aUnResponsable ? "ok" : "alerte"}">${icone(s.aUnResponsable ? "coche" : "employe", 20)}</span>
        <span class="texte"><strong>${echapper(s.nom)}</strong><small>${echapper(s.localisation)}</small></span>
        <span class="droite"><strong class="${s.aUnResponsable ? "ok" : "alerte"}">${s.aUnResponsable ? "Compte créé" : "Sans responsable"}</strong></span>`;
      return s.aUnResponsable ? `<div class="recent">${interieur}</div>`
        : `<button class="recent" data-sr="${echapper(s.id)}">${interieur}<span class="fleche">${icone("fleche", 18)}</span></button>`;
    }).join("")}</div>`;
    zone.querySelectorAll("[data-sr]").forEach((b) => b.addEventListener("click", () => aller(`#/sr/${b.dataset.sr}`)));
  } catch (e) {
    if (e.statut === 401) { fermerSession(); return; }
    zone.innerHTML = blocErreur(texteGestion(e));
  }
}

async function vueSRResponsable(id) {
  let sr = null;
  try { sr = (await api("/sr")).find((s) => s.id === id); } catch (e) { if (e.statut === 401) { fermerSession(); return; } }
  if (!sr || sr.aUnResponsable) { aller("#/sr"); return; }
  sousPage("Responsable du SR", `
    <div class="recap">${icone("batiment", 22)}<span><strong>${echapper(sr.nom)}</strong>${echapper(sr.localisation)}</span></div>
    <form id="formulaire" novalidate>${zoneErreur}
      ${champ("nom", "Nom et prénom", { maxlength: 200 })}
      ${champ("fonction", "Fonction", { valeur: "Pharmacien chef", maxlength: 100 })}
      ${champ("identifiantConnexion", "Identifiant de connexion", { autocapitalize: "none", spellcheck: "false", autocomplete: "off", maxlength: 100 })}
      ${champCourriel("", "Adresse personnelle de cette personne : elle recevra le lien en cas de mot de passe oublié")}
      ${champ("motDePasse", "Mot de passe initial", { type: "password", mdp: true, autocomplete: "new-password", aide: "8 caractères au moins", maxlength: 128 })}
      ${boutonGenerer}
      <button class="bouton" type="submit">Créer le compte</button>
    </form>`, "#/sr");
  const form = document.getElementById("formulaire");
  brancherChamps(form);
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (!valider(form, [["nom", regleNom], ["fonction", regleFonction], ["identifiantConnexion", regleIdentifiant], ["email", regleCourriel], ["motDePasse", () => (form.motDePasse.value.length >= 8 ? "" : "Le mot de passe compte au moins 8 caractères.")]])) return;
    soumettre(form, "Création du compte…", async () => {
      const mdp = form.motDePasse.value;
      const e = await api(`/sr/${id}/responsable`, { methode: "POST", json: { nom: form.nom.value.trim(), fonction: form.fonction.value.trim(), identifiantConnexion: form.identifiantConnexion.value.trim(), email: form.email.value.trim(), motDePasse: mdp } });
      afficherSucces({
        titre: "Compte responsable créé",
        sous: "Transmettez-lui son identifiant et son mot de passe initial.",
        lignes: [["Service régional", echapper(sr.nom)], ["Responsable", echapper(e.nom)], ["Identifiant", echapper(e.identifiantConnexion), "serie"], ["Mot de passe initial", echapper(mdp), "serie"]],
        boutons: [{ texte: "Autres services régionaux", icone: "batiment", clic: () => aller("#/sr") }, { texte: "Terminer", discret: true, clic: () => aller("#/") }],
      });
    });
  });
}

/* ------------------------------------------------------------------ Démarrage */

restaurerSession();
window.addEventListener("hashchange", rendre);
rendre();

// Au démarrage, la session enregistrée est vérifiée: fermée si le mot de passe a changé ailleurs, profil remis à jour sinon
if (etat.jeton) {
  api("/auth/moi").then((profil) => {
    if (!profil) return;
    const change = JSON.stringify(profil) !== JSON.stringify(etat.profil);
    etat.profil = profil; ecrire("session", { jeton: etat.jeton, profil });
    if (change && location.hash === "#/compte") rendre();
  }).catch((e) => { if (e.statut === 401) fermerSession(); /* hors connexion: on garde la session */ });
}

// La coque de l'application reste disponible sans réseau (adresse sécurisée ou localhost seulement)
if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")) {
  navigator.serviceWorker.register("sw.js", { scope: "./" }).catch(() => {});
}
