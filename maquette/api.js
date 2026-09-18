/* =============================================================================
   api.js — accès au noyau serveur (cycle 5, chantiers C9/C10).
   -----------------------------------------------------------------------------
   Fonctions partagées par les 4 écrans : session (jeton), appel des routes
   réelles du serveur (cycle 3), affichage des erreurs EN FRANÇAIS — jamais un
   message brut de fetch() ou de la console.

   Ce fichier ne contient AUCUNE règle métier de vente ou de stock : il relaie
   simplement ce que le serveur répond. Là où aucune route n'existe encore
   (ex. enregistrer une vente, lire les alertes de stock), les écrans gardent
   leurs données simulées de donnees-simulees.js et le signalent à l'écran —
   ce fichier n'invente rien à leur place.
   ============================================================================= */

const CLE_SESSION = "qf_session";

const RESEAU_INACCESSIBLE =
  "Impossible de contacter le serveur. Vérifiez qu'il est démarré, puis réessayez.";

// Délai maximal d'attente d'une réponse (UX-7, UX_BASELINE.md §4 bis, B9) :
// sans lui, fetch() ne rejette JAMAIS si la connexion est coupée EN COURS de
// requête (Wi-Fi qui tombe pendant une saisie) — contrairement au cas déjà
// géré d'un serveur injoignable dès le départ (refus de connexion immédiat).
// Constaté par un essai réel : une coupure simulée en cours de requête
// laissait l'écran tourner indéfiniment, sans aucun message, en violation de
// la règle du projet (jamais un écran figé sans indication). 20 s : assez
// large pour un export volumineux sur un réseau de boutique lent, assez
// court pour rester perçu comme "quelque chose ne va pas" par l'agent.
const DELAI_MAXI_REQUETE_MS = 20000;

// Libellés des deux sites. Fixes : creation_base_donnees.sql amorce
// exactement ces deux lignes dans la table "sites", immuables selon le
// cahier des charges (deux emplacements physiques, pas davantage à ce jour).
const LIBELLE_SITE = { 1: "Magasin de stock", 2: "Comptoir" };

const LIBELLE_ROLE = {
  responsable: "Responsable",
  agent_stock: "Agent stock",
  agent_comptabilite: "Agent comptabilité",
};

// Écran d'accueil par rôle, une fois connecté — un choix d'ergonomie (quel
// écran montrer en premier), pas une règle métier de vente ou de stock.
const PAGE_ACCUEIL_PAR_ROLE = {
  responsable: "tableau-bord.html",
  agent_comptabilite: "vente.html",
  agent_stock: "inventaire.html",
};

const Session = {
  enregistrer(donnees) {
    sessionStorage.setItem(CLE_SESSION, JSON.stringify(donnees));
  },
  lire() {
    try {
      const brut = sessionStorage.getItem(CLE_SESSION);
      return brut ? JSON.parse(brut) : null;
    } catch {
      return null;
    }
  },
  effacer() {
    sessionStorage.removeItem(CLE_SESSION);
  },
};

async function lireJsonSecurise(reponse) {
  try {
    return await reponse.json();
  } catch {
    return null;
  }
}

/**
 * Fait la requête authentifiée et la traduction d'erreur commune à
 * appelApi() et telechargerFichier() (cycle 12) — renvoie la Response
 * BRUTE (pas encore lue), pour que l'appelant choisisse .json() ou .blob().
 */
async function appelApiBrut(chemin, options = {}) {
  const session = Session.lire();
  const entetes = Object.assign({}, options.headers || {});
  if (session && session.jeton) entetes["Authorization"] = "Bearer " + session.jeton;
  // FormData (téléversement de fichier, cycle 28) : jamais fixer nous-mêmes
  // Content-Type — le navigateur doit poser lui-même la frontière multipart
  // (boundary), qu'il calcule à l'envoi. Un Content-Type ici, même correct
  // en apparence, casserait l'analyse côté serveur (frontière manquante).
  const estFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (options.body && !estFormData && !entetes["Content-Type"]) entetes["Content-Type"] = "application/json";

  // AbortController : seul moyen de faire échouer fetch() par nous-mêmes
  // quand le réseau se coupe SANS refus explicite (voir DELAI_MAXI_REQUETE_MS
  // ci-dessus) — sans lui, la requête resterait en attente indéfiniment.
  const limiteur = new AbortController();
  const declencheurDelai = setTimeout(() => limiteur.abort(), DELAI_MAXI_REQUETE_MS);

  let reponse;
  try {
    reponse = await fetch(chemin, Object.assign({}, options, { headers: entetes, signal: limiteur.signal }));
  } catch {
    // Refus de connexion immédiat (serveur éteint) ET dépassement du délai
    // (coupure en cours de requête, AbortError) aboutissent au même message
    // clair : dans les deux cas, l'agent ne peut rien faire de plus qu'un
    // simple "réessayez" — jamais un écran qui tourne sans explication.
    const erreur = new Error(RESEAU_INACCESSIBLE);
    erreur.reseauIndisponible = true;
    throw erreur;
  } finally {
    clearTimeout(declencheurDelai);
  }

  if (!reponse.ok) {
    if (reponse.status === 401) Session.effacer();
    const corps = await lireJsonSecurise(reponse);
    const erreur = new Error((corps && corps.detail) || "Le serveur a refusé la demande.");
    erreur.statut = reponse.status;
    throw erreur;
  }
  return reponse;
}

/**
 * Appelle une route du serveur en ajoutant automatiquement le jeton de
 * session. Lève une Error au message déjà en français (celui du serveur pour
 * un refus, un message générique pour une panne réseau) — jamais l'erreur
 * brute de fetch().
 */
async function appelApi(chemin, options = {}) {
  const reponse = await appelApiBrut(chemin, options);
  if (reponse.status === 204) return null;
  return lireJsonSecurise(reponse);
}

/**
 * Télécharge un fichier authentifié (export Excel/PDF, cycle 12) : un lien
 * <a href> nu ne peut pas porter le jeton de session, donc on lit la
 * réponse en blob() et on simule un clic sur une ancre temporaire — seule
 * façon de déclencher un téléchargement de navigateur pour une requête qui
 * doit passer par fetch(). Le nom de fichier vient du Content-Disposition
 * du serveur (routes/rapports.py) si présent, sinon d'une valeur de repli.
 */
async function telechargerFichier(chemin, nomFichierParDefaut) {
  const reponse = await appelApiBrut(chemin);
  const blob = await reponse.blob();
  const entete = reponse.headers.get("Content-Disposition") || "";
  const correspondance = /filename="([^"]+)"/.exec(entete);
  const nomFichier = correspondance ? correspondance[1] : nomFichierParDefaut;

  const url = URL.createObjectURL(blob);
  const lien = document.createElement("a");
  lien.href = url;
  lien.download = nomFichier;
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
  URL.revokeObjectURL(url);
}

/**
 * Vérifie, RÉELLEMENT auprès du serveur (GET /moi — pas seulement en lisant
 * le stockage local), qu'une session valide existe et que le rôle est
 * autorisé sur cet écran. Redirige sinon (session absente/expirée -> écran
 * de connexion ; rôle non autorisé -> écran d'accueil de ce rôle). À appeler
 * au chargement de chaque écran protégé, avant tout affichage de donnée.
 */
async function exigerSession(rolesAutorises) {
  const session = Session.lire();
  if (!session || !session.jeton) {
    window.location.href = "connexion.html";
    return null;
  }
  try {
    const profil = await appelApi("/moi");
    const fusion = Object.assign({}, session, profil);
    Session.enregistrer(fusion);
    if (rolesAutorises && !rolesAutorises.includes(profil.role)) {
      window.location.href = PAGE_ACCUEIL_PAR_ROLE[profil.role] || "connexion.html";
      return null;
    }
    return fusion;
  } catch {
    window.location.href = "connexion.html";
    return null;
  }
}

/** Affiche un message d'erreur SERVEUR près d'un champ/zone donné — jamais
 * une alert() ni une exception non attrapée dans la console. */
function afficherErreurServeur(zoneId, erreur) {
  const zone = document.getElementById(zoneId);
  if (!zone) return;
  zone.textContent = erreur && erreur.message ? erreur.message : "Une erreur est survenue.";
  zone.hidden = false;
}

/**
 * Déconnexion RÉELLE (chantier C11, cycle 21) : révoque le jeton côté
 * serveur (POST /auth/deconnexion) avant de l'effacer localement — jusqu'ici
 * "se déconnecter" ne faisait que vider le stockage local, le jeton restait
 * valide jusqu'à sa propre expiration si quelqu'un d'autre l'avait intercepté.
 * La révocation reste du "meilleur effort" : un réseau coupé au moment du
 * clic ne doit jamais empêcher de quitter l'écran localement.
 */
async function deconnecter() {
  try {
    await appelApi("/auth/deconnexion", { method: "POST" });
  } catch {
    // Volontairement ignoré : voir le commentaire ci-dessus.
  }
  Session.effacer();
  window.location.href = "connexion.html";
}

/** Affichage des montants en francs CFA (pas de sous-unité). Partagé par
 * les écrans qui affichent un prix (vente.html, tableau-bord.html,
 * stock.html pour un responsable) — jamais chargé côté logique de
 * l'agent stock. */
function fcfa(montant) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Math.round(montant)) + " FCFA";
}

/**
 * Construit un <li> "libellé + sous-texte + pastille" (alertes, écarts...)
 * SANS jamais passer par innerHTML : un nom d'article vient du serveur et
 * reste modifiable par le personnel, ce n'est pas un texte fixe — le
 * concaténer dans du HTML permettrait d'y injecter des balises. Trouvé et
 * corrigé lors du contrôle de boucle après le cycle 7 (tableau-bord.html
 * construisait ses listes ainsi, à trois endroits, avec des données réelles
 * pour deux d'entre eux).
 */
function creerLigneListe(libellePrincipal, sousTexte, texteAside, classeAside) {
  const li = document.createElement("li");

  const spanPrincipal = document.createElement("span");
  // UX-3 (UX_BASELINE.md §4 bis, B2) : sans ceci, un libellé réel un peu
  // plus long que le jeu d'essai des suites automatisées (nom d'article,
  // motif) peut forcer TOUTE la ligne — et donc la grille de cartes qui la
  // contient — plus large que l'écran sur un vrai téléphone, sans jamais se
  // reproduire avec les libellés courts et fixes utilisés par les tests.
  spanPrincipal.style.minWidth = "0";
  spanPrincipal.style.overflowWrap = "anywhere";
  spanPrincipal.appendChild(document.createTextNode(libellePrincipal));
  spanPrincipal.appendChild(document.createElement("br"));
  const spanSous = document.createElement("span");
  spanSous.style.color = "var(--c-texte-doux)";
  spanSous.style.fontSize = "var(--t-xs)";
  spanSous.textContent = sousTexte;
  spanPrincipal.appendChild(spanSous);

  const spanAside = document.createElement("span");
  spanAside.className = "pastille " + classeAside;
  spanAside.textContent = texteAside;

  li.appendChild(spanPrincipal);
  li.appendChild(spanAside);
  return li;
}

/**
 * Insère le logo DE LA BOUTIQUE CLIENTE (cycle 28) dans le bandeau de
 * l'écran courant, juste après la marque Akuma (bandeau__marque) — distinct
 * du logo Akuma lui-même, jamais remplaçable par l'utilisateur, qui reste
 * un fichier statique de la maquette.
 *
 * GET /configuration/logo est PUBLIC (voir server/app/routes/
 * configuration.py) : aucun jeton nécessaire, appelable même avant
 * connexion. `onerror` retire l'élément proprement si aucun logo n'a été
 * téléversé — jamais une image cassée, jamais un espace vide réservé.
 */
function afficherLogoBoutiqueDansBandeau() {
  const bandeau = document.querySelector(".bandeau");
  if (!bandeau) return;
  const img = document.createElement("img");
  img.alt = "Logo de la boutique";
  img.className = "logo-boutique-bandeau";
  img.onerror = () => img.remove();
  img.src = "/configuration/logo?t=" + Date.now();
  const marque = bandeau.querySelector(".bandeau__marque");
  if (marque && marque.parentNode) {
    marque.insertAdjacentElement("afterend", img);
  } else {
    bandeau.prepend(img);
  }
}
