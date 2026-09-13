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
  if (options.body && !entetes["Content-Type"]) entetes["Content-Type"] = "application/json";

  let reponse;
  try {
    reponse = await fetch(chemin, Object.assign({}, options, { headers: entetes }));
  } catch {
    const erreur = new Error(RESEAU_INACCESSIBLE);
    erreur.reseauIndisponible = true;
    throw erreur;
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
