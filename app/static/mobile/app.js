// Application mobile de traçabilité des médicaments.
// Écrans: connexion (fiche 1), accueil, réception et expédition (fiche 7), dispensation (fiche 8),
// statut d'une unité (fiche 9), compte. Tout passe par l'API, sur la même adresse que cette page.

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
  scan: (t) => trait('<path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>', t),
};
const icone = (nom, taille = 24) => ICONES[nom](taille);

// Le motif de l'application: un DataMatrix (bord gauche et bas pleins, bord haut et droit en pointillés)
function marque(taille = 32) {
  return `<svg class="marque" width="${taille}" height="${taille}" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="3.2" aria-hidden="true">
    <path d="M4.5 4.5v23h23"/><path d="M4.5 4.5h23" stroke-dasharray="3.6 3.6"/><path d="M27.5 4.5v23" stroke-dasharray="3.6 3.6"/>
    <path d="M11 11h4v4h-4zM17 17h4v4h-4z" fill="currentColor" stroke="none"/></svg>`;
}

// Texture de modules DataMatrix pour l'en-tête de connexion (suite pseudo-aléatoire fixe, donc stable)
function motif() {
  let graine = 7, rects = "";
  const alea = () => (graine = (graine * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const colonnes = 22, lignes = 16, c = 18;
  for (let y = 0; y < lignes; y++) {
    for (let x = 0; x < colonnes; x++) {
      const proba = 0.62 - y * 0.034 + (x > 11 ? 0.05 : 0);
      if (alea() < proba) rects += `<rect x="${x * c}" y="${y * c}" width="${c - 5}" height="${c - 5}" rx="1.5" opacity="${(0.25 + alea() * 0.75).toFixed(2)}"/>`;
    }
  }
  return `<svg class="motif" viewBox="0 0 ${colonnes * c} ${lignes * c}" preserveAspectRatio="xMidYMin slice" fill="currentColor" aria-hidden="true">${rects}</svg>`;
}

/* ------------------------------------------------------------------ État et stockage */

const etat = { jeton: null, profil: null, resultat: null, nettoyage: null };

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
  const liste = [entree, ...recents()].slice(0, 20);
  ecrire(cleRecents(), liste);
}

/* ------------------------------------------------------------------ API */

class ErreurApi extends Error {
  constructor(statut, detail) { super(detail || `Erreur ${statut}`); this.statut = statut; this.detail = detail || ""; }
}

async function api(chemin, { methode = "GET", corps, formulaire } = {}) {
  const entetes = {};
  if (etat.jeton) entetes.Authorization = `Bearer ${etat.jeton}`;
  let reponse;
  try {
    reponse = await fetch(chemin, { method: methode, headers: entetes, body: formulaire || corps });
  } catch {
    throw new ErreurApi(0, "reseau");
  }
  let donnees = null;
  try { donnees = await reponse.json(); } catch { /* corps vide ou non JSON */ }
  if (!reponse.ok) {
    const d = donnees && donnees.detail;
    const detail = typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg).join(" ") : "";
    throw new ErreurApi(reponse.status, detail);
  }
  return donnees;
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
  if (!etat.jeton) { vueConnexion(); return; }
  if (hash === "#/connexion") { aller("#/"); return; }
  if (etat.profil.structure_type === "PNA") { vuePna(); return; }
  const m = hash.match(/^#\/scan\/(\w+)$/);
  if (m && OPERATIONS[m[1]] && AUTORISEES[etat.profil.structure_type].includes(m[1])) { vueScanner(m[1]); return; }
  if (hash === "#/resultat" && etat.resultat) { vueResultat(); return; }
  if (hash === "#/compte") { vueCompte(); return; }
  vueAccueil();
}

/* ------------------------------------------------------------------ Connexion */

function vueConnexion(erreur = "") {
  racine.innerHTML = `
    <header class="connexion-tete">
      ${motif()}
      <div class="contenu">
        ${marque(44)}
        <h1>Traçabilité des médicaments</h1>
        <p>Suivez chaque unité, de la fabrication à la dispensation.</p>
      </div>
    </header>
    <main class="connexion-corps">
      <form id="formulaire" novalidate>
        <div id="erreur" role="alert">${erreur ? blocErreur(erreur) : ""}</div>
        <label class="champ"><span>Identifiant de connexion</span>
          <div class="saisie"><input name="identifiant" autocomplete="username" autocapitalize="none" spellcheck="false" required></div>
        </label>
        <label class="champ"><span>Mot de passe</span>
          <div class="saisie"><input name="mdp" type="password" autocomplete="current-password" required>
            <button type="button" class="oeil" data-action="oeil" aria-label="Afficher le mot de passe">${icone("oeil")}</button></div>
        </label>
        <button class="bouton" type="submit">Se connecter</button>
      </form>
    </main>`;
  const formulaire = document.getElementById("formulaire");
  formulaire.identifiant.focus({ preventScroll: true });
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
      bouton.disabled = false; bouton.textContent = "Se connecter";
    }
  });
}
const blocErreur = (texte) => `<div class="message-erreur">${icone("attention", 20)}<span>${echapper(texte)}</span></div>`;

/* ------------------------------------------------------------------ Barre du bas et feuille des opérations */

function barre(actif) {
  return `<nav class="barre" aria-label="Navigation principale">
    <button class="onglet" data-aller="#/" ${actif === "accueil" ? 'aria-current="page"' : ""}>${icone("accueil")}Accueil</button>
    <button class="bouton-scan" data-action="choisir" aria-label="Scanner une unité">${icone("scan", 30)}</button>
    <button class="onglet" data-aller="#/compte" ${actif === "compte" ? 'aria-current="page"' : ""}>${icone("compte")}Compte</button>
  </nav>`;
}

function brancherBarre() {
  racine.querySelectorAll("[data-aller]").forEach((b) => b.addEventListener("click", () => aller(b.dataset.aller)));
  racine.querySelector('[data-action="choisir"]')?.addEventListener("click", ouvrirChoix);
}

function ouvrirChoix() {
  const ops = AUTORISEES[etat.profil.structure_type];
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

function vueAccueil() {
  const p = etat.profil, ops = AUTORISEES[p.structure_type], principale = PRINCIPALE[p.structure_type];
  const liste = recents().slice(0, 5);
  racine.innerHTML = `
    <main class="page">
      <header class="entete"><span class="marque">${marque(28)}Traçabilité</span>
        <button class="avatar" data-aller="#/compte" aria-label="Mon compte">${echapper(initiales(p.nom))}</button></header>
      <section class="accueil-titre">
        <div class="bonjour">Bonjour, ${echapper(p.nom)}</div>
        <h1>${echapper(p.structure_nom)}</h1>
        <span class="puce">${TYPES_STRUCTURE[p.structure_type] || p.structure_type}</span>
      </section>
      <h2 class="section-titre">Que voulez-vous faire ?</h2>
      <div class="actions">${ops.map((o) => ligneAction(o, o === principale)).join("")}</div>
      <h2 class="section-titre">Récents sur cet appareil</h2>
      ${liste.length ? `<div class="recents">${liste.map(ligneRecent).join("")}</div>`
        : `<div class="recents"><div class="vide"><strong>Aucune opération pour l'instant</strong>Les unités que vous scannez apparaîtront ici.</div></div>`}
      ${liste.length ? '<p class="mention">Appuyez sur une unité pour revoir son statut. Liste conservée sur cet appareil seulement.</p>' : ""}
    </main>${barre("accueil")}`;
  brancherBarre();
  racine.querySelectorAll("[data-op]").forEach((b) => b.addEventListener("click", () => aller(`#/scan/${b.dataset.op}`)));
  racine.querySelectorAll("[data-serie]").forEach((b) => b.addEventListener("click", () => verifierRecent(b.dataset.serie)));
}

function ligneRecent(r) {
  const o = OPERATIONS[r.op];
  const classe = r.issue === "ok" ? "ok" : r.issue === "alerte" ? "alerte" : "refus";
  const mot = { ok: "Enregistrée", alerte: "À vérifier", refus: "Refusée" }[r.issue];
  const symbole = icone({ ok: "coche", alerte: "attention", refus: "croix" }[r.issue], 20);
  const interieur = `<span class="pastille ${classe}">${symbole}</span>
    <span class="texte"><strong>${o.titre}</strong><small>${echapper(r.serie)}</small></span>
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

/* ------------------------------------------------------------------ Compte et PNA */

function vueCompte() {
  const p = etat.profil;
  racine.innerHTML = `<main class="page">
    <header class="entete"><span class="marque">${marque(28)}Compte</span></header>
    <section class="compte-carte"><div class="avatar">${echapper(initiales(p.nom))}</div>
      <h2>${echapper(p.nom)}</h2><p>${echapper(p.fonction)}</p>
      <p>${echapper(p.structure_nom)}</p><span class="puce">${TYPES_STRUCTURE[p.structure_type] || p.structure_type}</span></section>
    <div style="margin-top:20px"><button class="bouton discret" data-action="sortir">${icone("deconnexion", 20)}Se déconnecter</button></div>
  </main>${barre("compte")}`;
  brancherBarre();
  racine.querySelector('[data-action="sortir"]').addEventListener("click", fermerSession);
}

function vuePna() {
  racine.innerHTML = `<main class="pna-message page">${marque(40)}
    <h1 style="margin-top:20px">Cette application est destinée aux structures du circuit</h1>
    <p>Fabricants, grossistes, services régionaux et officines scannent et vérifient les unités ici. Le suivi de la pharmacie nationale se fait dans la vue SIG.</p>
    <button class="bouton discret" data-action="sortir">${icone("deconnexion", 20)}Se déconnecter</button></main>`;
  racine.querySelector('[data-action="sortir"]').addEventListener("click", fermerSession);
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
    if (fichier) f.append("image", fichier, fichier.name || "code.jpg");
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
      <div class="poignee"></div><h2>Numéro de série</h2><p class="aide">Saisissez le numéro de série de l'unité.</p>
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
    sous = r.op === "dispensation"
      ? "Aucune réception par cette officine dans l'historique de l'unité. À faire vérifier."
      : "Cet identifiant était déjà désactivé. L'événement est gardé avec une alerte à vérifier.";
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

/* ------------------------------------------------------------------ Démarrage */

restaurerSession();
window.addEventListener("hashchange", rendre);
rendre();

// La coque de l'application reste disponible sans réseau (adresse sécurisée ou localhost seulement)
if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")) {
  navigator.serviceWorker.register("sw.js", { scope: "./" }).catch(() => {});
}
