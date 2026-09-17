/* Vérifie, PAR EXÉCUTION RÉELLE contre le noyau serveur (cycle 3) démarré et
   servant la maquette sous /app (cycle 5, chantiers C9/C10), que :

   1. les 3 rôles se connectent réellement et sont redirigés vers leur écran
      d'accueil ;
   2. le CONTENU des réponses du serveur diffère par rôle : l'agent stock ne
      reçoit AUCUN champ de prix, le comptable AUCUN champ de quantité ;
   3. la quantité attendue d'un comptage n'apparaît JAMAIS dans une réponse
      réseau ni dans le contenu de la page d'inventaire ;
   4. les messages d'erreur serveur s'affichent en français, près du champ
      concerné (jamais un message brut) ;
   5. les 4 écrans s'affichent sans débordement aux 5 largeurs, avec de vrais
      comptes connectés là où c'est pertinent.

   Prérequis :
     - PostgreSQL de développement démarré (db/outils/demarrer_pg.ps1) ;
     - le noyau serveur démarré et servant /app :
         server\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir server --port 8010
   (SERVEUR_URL par défaut : http://127.0.0.1:8010)

   Ce script réinitialise LUI-MÊME la base (jeu d'essai + mots de passe bcrypt
   réels pour les 3 comptes de test), pour rester rejouable de façon fiable.
*/
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { existsSync } from "node:fs";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE_DEPOT = resolve(ICI, "..", "..");
const CAPTURES = resolve(ICI, "..", "captures") + "/";

const SERVEUR_URL = process.env.SERVEUR_URL || "http://127.0.0.1:8010";
const DB_PISTE = process.env.PGDATABASE_PISTE || "quincaillerie_test";
let PGDEV = resolve(RACINE_DEPOT, "_pgdev");
if (!existsSync(PGDEV)) {
  // _pgdev/ n'existe que dans le dépôt principal, pas dans un worktree Git
  // (RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md) : on bascule sur celui du dépôt
  // principal, deux niveaux au-dessus de _worktrees/<piste>/.
  PGDEV = resolve(RACINE_DEPOT, "..", "..", "_pgdev");
}
const PSQL = resolve(PGDEV, "pgsql", "bin", "psql.exe");

const MDP_RESPONSABLE = "ResponsableTest123";
const MDP_AGENT_STOCK = "AgentStockTest123";
const MDP_AGENT_COMPTA = "AgentComptaTest123";

const ok = [], ko = [];
const verifier = (cond, libelle) => (cond ? ok : ko).push(libelle);

function psql(sql) {
  execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE, "-q", "-c", sql,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
}

function psqlFichier(chemin) {
  execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
    "-v", "ON_ERROR_STOP=1", "-q", "-f", chemin,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
}

console.log("== Préparation de la base (jeu d'essai + comptes de test) ==");
psqlFichier(resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"));
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
// Deux ventes réelles du jour, pour que le tableau de bord du responsable
// montre une vraie synthèse consolidée (un site chacun).
psql(`INSERT INTO ventes (site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc, utilisateur_caisse_id, mode_paiement, date_encaissement)
       VALUES (1, 4, 'payee', 6500, 0, 0, 6500, 1, 'especes', NOW());`);
psql(`INSERT INTO ventes (site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc, utilisateur_caisse_id, mode_paiement, date_encaissement)
       VALUES (2, 5, 'payee', 3200, 0, 0, 3200, 1, 'especes', NOW());`);
console.log("Base prête.\n");

const navigateur = await chromium.launch({ channel: "chrome" });

async function nouvellePage(largeur = 1366, hauteur = 900) {
  const contexte = await navigateur.newContext({ viewport: { width: largeur, height: hauteur } });
  const page = await contexte.newPage();
  if (process.env.DEBUG_CABLAGE) {
    page.on("console", (m) => console.log("  [console]", m.type(), m.text()));
    page.on("pageerror", (e) => console.log("  [pageerror]", e.message));
    page.on("requestfailed", (r) => console.log("  [requestfailed]", r.url(), r.failure()?.errorText));
  }
  return { contexte, page };
}

async function seConnecter(page, identifiant, motDePasse) {
  await page.goto(`${SERVEUR_URL}/app/connexion.html`, { waitUntil: "networkidle" });
  await page.fill("#identifiant", identifiant);
  await page.fill("#motdepasse", motDePasse);
  // On attend la VRAIE réponse HTTP du serveur plutôt que l'heuristique
  // "networkidle" (observée peu fiable ici pour enchaîner deux navigations
  // successives — connexion.html -> redirection JS -> nouvel écran) : le
  // clic peut se résoudre avant que la réponse ne soit reçue, ou l'inverse.
  const [reponse] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/auth/connexion"), { timeout: 10000 }),
    page.click("#bouton-connexion"),
  ]);
  if (reponse.ok()) {
    await page.waitForURL((u) => !u.pathname.endsWith("connexion.html"), { timeout: 10000 });
    await page.waitForLoadState("networkidle");
  }
}

function verifierMiseEnPage(nomEcran, largeur, metriques) {
  verifier(!metriques.overflowH, `${nomEcran}@${largeur} : aucun débordement horizontal`);
  if (metriques.cibleMin !== null) {
    verifier(largeur > 768 || metriques.cibleMin >= 44, `${nomEcran}@${largeur} : cible tactile mini ${metriques.cibleMin}px ≥ 44px`);
  }
}

async function mesurerEtCapturer(page, nomEcran, largeur) {
  const metriques = await page.evaluate(() => {
    const de = document.documentElement, vw = window.innerWidth;
    const cibles = [...document.querySelectorAll("button, a, input, select")]
      .map((el) => Math.round(el.getBoundingClientRect().height)).filter((h) => h > 0);
    return {
      overflowH: de.scrollWidth > de.clientWidth + 1,
      cibleMin: cibles.length ? Math.min(...cibles) : null,
    };
  });
  await page.screenshot({ path: `${CAPTURES}${nomEcran}-${largeur}.png`, fullPage: true });
  verifierMiseEnPage(nomEcran, largeur, metriques);
}

const LARGEURS = [360, 390, 768, 1366, 1920];

// ============================================================================
// 1. Connexion — layout aux 5 largeurs, sans session
// ============================================================================
for (const largeur of LARGEURS) {
  const { contexte, page } = await nouvellePage(largeur, largeur < 700 ? 780 : largeur < 1400 ? 800 : 960);
  await page.goto(`${SERVEUR_URL}/app/connexion.html`, { waitUntil: "networkidle" });
  await mesurerEtCapturer(page, "connexion", largeur);
  await contexte.close();
}

// ============================================================================
// 2. Connexion — messages d'erreur réels, en français, près du champ
// ============================================================================
{
  const { contexte, page } = await nouvellePage();
  await page.goto(`${SERVEUR_URL}/app/connexion.html`, { waitUntil: "networkidle" });

  await page.click("#bouton-connexion");
  verifier(
    (await page.textContent("#zone-erreur")).includes("Saisissez votre identifiant"),
    "connexion : champs vides -> erreur explicite près du champ"
  );

  await page.fill("#identifiant", "resp");
  await page.fill("#motdepasse", "mauvais");
  await page.click("#bouton-connexion");
  await page.locator("#zone-erreur:not([hidden])").waitFor({ timeout: 10000 });
  verifier(
    (await page.textContent("#zone-erreur")) === "Identifiant ou mot de passe incorrect.",
    "connexion : mauvais mot de passe -> message exact du serveur, en français"
  );

  // Panne réseau simulée (fetch intercepté) : jamais un message brut.
  await page.route("**/auth/connexion", (route) => route.abort("failed"));
  await page.fill("#identifiant", "resp");
  await page.fill("#motdepasse", MDP_RESPONSABLE);
  await page.click("#bouton-connexion");
  await page.waitForFunction(
    () => document.getElementById("zone-erreur").textContent.includes("Impossible"),
    { timeout: 10000 }
  );
  const messageReseau = await page.textContent("#zone-erreur");
  verifier(
    messageReseau.startsWith("Impossible de contacter le serveur"),
    `connexion : serveur injoignable -> message français, pas une erreur brute ("${messageReseau}")`
  );
  await contexte.close();
}

// ============================================================================
// 3. Agent stock -> redirigé vers inventaire.html ; AUCUN prix nulle part
// ============================================================================
{
  const { contexte, page } = await nouvellePage();
  await seConnecter(page, "magasin.stock", MDP_AGENT_STOCK);
  verifier(page.url().endsWith("inventaire.html"), "agent stock : connexion -> redirigé vers inventaire.html");

  // Tentative d'accéder à vente.html quand même : redirigé vers son écran.
  // (exigerSession fait GET /moi puis window.location.href — deux allers-retours
  // réseau après le premier "networkidle" du goto ci-dessous, d'où l'attente
  // explicite de l'URL finale plutôt qu'un délai fixe.)
  await page.goto(`${SERVEUR_URL}/app/vente.html`);
  await page.waitForURL(/inventaire\.html/, { timeout: 10000 });
  await page.waitForLoadState("networkidle");
  verifier(page.url().endsWith("inventaire.html"), "agent stock : accès direct à vente.html -> reredirigé");

  // Identité réelle affichée.
  verifier(
    (await page.textContent("#entete-role")).includes("Agent stock"),
    "agent stock : identité réelle affichée dans le bandeau"
  );

  // Le CONTENU de /articles ne contient AUCUN champ de prix — vérifié en
  // relisant la réponse réelle reçue par la page (pas une supposition).
  const articles = await page.evaluate(async () => {
    const session = JSON.parse(sessionStorage.getItem("qf_session"));
    const r = await fetch("/articles", { headers: { Authorization: "Bearer " + session.jeton } });
    return r.json();
  });
  const champsInterdits = new Set();
  articles.articles.forEach((a) => Object.keys(a).forEach((k) => {
    if (/prix|montant/i.test(k)) champsInterdits.add(k);
  }));
  verifier(champsInterdits.size === 0, `agent stock : /articles sans AUCUN champ de prix (trouvé : ${[...champsInterdits].join(",") || "aucun"})`);
  verifier(articles.articles.length > 0, "agent stock : /articles renvoie au moins un article");
  verifier(articles.articles.every((a) => a.site_id === 1), "agent stock : /articles limité au site 1 (Magasin de stock)");

  await mesurerEtCapturer(page, "inventaire", page.viewportSize().width);
  for (const largeur of LARGEURS) {
    await page.setViewportSize({ width: largeur, height: largeur < 700 ? 780 : largeur < 1400 ? 800 : 960 });
    await mesurerEtCapturer(page, "inventaire", largeur);
  }

  // --- LE POINT LE PLUS IMPORTANT : la quantité attendue ne fuite NULLE PART ---
  const reponsesVues = [];
  page.on("response", async (reponse) => {
    if (reponse.url().startsWith(SERVEUR_URL) && reponse.headers()["content-type"]?.includes("json")) {
      try { reponsesVues.push(await reponse.text()); } catch { /* réponse déjà consommée */ }
    }
  });
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(300);

  const contenuPage = await page.content();
  const motifsInterdits = /quantite_attendue|quantité attendue|"attendu"|attendu\s*:/i;
  verifier(!motifsInterdits.test(contenuPage), "inventaire : aucune 'quantité attendue' dans le HTML rendu");
  verifier(
    reponsesVues.every((corps) => !motifsInterdits.test(corps)),
    `inventaire : aucune 'quantité attendue' dans les ${reponsesVues.length} réponse(s) réseau observée(s)`
  );
  const source = await page.evaluate(() => document.documentElement.outerHTML);
  verifier(!motifsInterdits.test(source), "inventaire : aucune 'quantité attendue' dans le code source de la page");

  await contexte.close();
}

// ============================================================================
// 4. Agent comptabilité -> redirigé vers vente.html ; AUCUNE quantité nulle part
// ============================================================================
{
  const { contexte, page } = await nouvellePage();
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);
  verifier(page.url().endsWith("vente.html"), "agent comptabilité : connexion -> redirigé vers vente.html");
  verifier(
    (await page.textContent("#badge-utilisateur")).includes("Agent comptabilité"),
    "agent comptabilité : identité réelle affichée dans le bandeau"
  );

  const articles = await page.evaluate(async () => {
    const session = JSON.parse(sessionStorage.getItem("qf_session"));
    const r = await fetch("/articles", { headers: { Authorization: "Bearer " + session.jeton } });
    return r.json();
  });
  const champsInterdits = new Set();
  articles.articles.forEach((a) => Object.keys(a).forEach((k) => {
    if (/quantite|seuil/i.test(k)) champsInterdits.add(k);
  }));
  verifier(champsInterdits.size === 0, `agent comptabilité : /articles sans AUCUN champ de quantité (trouvé : ${[...champsInterdits].join(",") || "aucun"})`);
  verifier(articles.articles.every((a) => "prix_vente" in a), "agent comptabilité : /articles contient bien le prix de vente");
  verifier(articles.articles.every((a) => a.site_id === 1), "agent comptabilité : /articles limité au site 1 (Magasin de stock)");

  // Recherche réelle dans le catalogue : un article de l'AUTRE site n'apparaît pas.
  await page.fill("#recherche", "clou"); // "Clou 5 cm" appartient au Comptoir (site 2)
  await page.waitForTimeout(150);
  verifier(
    await page.getAttribute("#suggestions", "hidden") !== null,
    "agent comptabilité : recherche d'un article de l'autre site -> aucun résultat"
  );
  await page.fill("#recherche", "rare"); // "Article rare" existe au Magasin (site 1)
  await page.waitForTimeout(150);
  verifier(
    (await page.textContent("#suggestions")).includes("Article rare"),
    "agent comptabilité : recherche d'un article de son site -> trouvé"
  );
  await page.keyboard.press("Enter");
  await page.waitForTimeout(100);
  verifier(
    (await page.textContent("#dernier-ajout")).includes("Article rare"),
    "agent comptabilité : article réel ajouté au panier avec son vrai prix"
  );

  // Validation RÉELLE depuis le cycle 6 (chantier C5, POST /ventes) : plus de
  // mention SIMULATION, un vrai numéro de vente apparaît. Le contrôle détaillé
  // de cette route (TVA, écarts, crédit désactivé...) est dans
  // verifier-vente-reelle.mjs ; on vérifie ici seulement que l'écran l'utilise
  // vraiment, pas que la maquette invente encore une confirmation locale.
  await page.keyboard.press("F9");
  await page.keyboard.press("F9");
  await page.waitForFunction(() => !document.getElementById("zone-succes").hidden, { timeout: 10000 });
  const messageValidation = await page.textContent("#zone-succes");
  verifier(/^Vente n°\d+ enregistrée/.test(messageValidation), `vente : validation réelle, numéro de vente renvoyé par le serveur ("${messageValidation}")`);
  verifier(!/SIMULATION/i.test(messageValidation), "vente : plus aucune confirmation inventée localement");

  for (const largeur of LARGEURS) {
    await page.setViewportSize({ width: largeur, height: largeur < 700 ? 780 : largeur < 1400 ? 800 : 960 });
    await mesurerEtCapturer(page, "vente", largeur);
  }
  await contexte.close();
}

// ============================================================================
// 5. Responsable -> tableau de bord ; ventes du jour RÉELLES, consolidées
// ============================================================================
{
  const { contexte, page } = await nouvellePage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  verifier(page.url().endsWith("tableau-bord.html"), "responsable : connexion -> redirigé vers tableau-bord.html");
  verifier(
    (await page.textContent("#entete-role")).includes("Responsable"),
    "responsable : identité réelle affichée dans le bandeau"
  );

  await page.waitForSelector("#ventes-jour dl", { timeout: 5000 });
  const texteVentes = await page.textContent("#ventes-jour");
  verifier(texteVentes.includes("Magasin de stock"), "responsable : ventes du jour réelles -> site Magasin de stock présent");
  verifier(texteVentes.includes("Comptoir"), "responsable : ventes du jour réelles -> site Comptoir présent (consolidé)");
  // 9700 (les deux ventes semées ci-dessus) + 2000 (la vente RÉELLE créée
  // plus haut, section agent comptabilité, en validant "Article rare" par
  // POST /ventes — chantier C5, cycle 6) = 11700.
  const totalTexte = await page.textContent("#ventes-total");
  verifier(totalTexte.includes("11") && totalTexte.includes("700"), `responsable : total consolidé correct (lu : "${totalTexte}")`);

  // Depuis le cycle 8, « Alertes de stock faible » est câblée pour de vrai
  // (chantier C8) : plus aucune carte du tableau de bord n'est simulée.
  const cartesSimulees = await page.$$eval(".pastille--neutre", (els) => els.map((e) => e.textContent));
  verifier(cartesSimulees.length === 0,
    "tableau de bord : plus aucune carte marquée « donnée simulée » (C8 câblé)");

  // « Article rare » (jeu d'essai, quantité 1 pour un seuil de 1) doit
  // apparaître dans les alertes de stock, réellement lues via
  // /tableau-bord/alertes-stock — pas la donnée simulée d'avant le cycle 8
  // (qui citait "Ciment CIM II 50 kg", "Peinture blanche 4 L"...).
  await page.waitForSelector("#liste-alertes li", { timeout: 5000 });
  const texteAlertes = await page.textContent("#liste-alertes");
  verifier(texteAlertes.includes("Article rare"), "responsable : alerte de stock réelle -> « Article rare » présent");
  verifier(!texteAlertes.includes("Peinture blanche"), "responsable : alerte de stock réelle -> ancienne donnée simulée absente");

  // --- Bascule vue consolidée / par site (chantier C8, cycle 23) : filtre
  // purement d'affichage, aucun nouvel appel réseau au changement de vue.
  // Magasin de stock (site 1) : 6500 (semée) + 2000 (vente réelle, section
  // agent comptabilité ci-dessus) = 8500. Comptoir (site 2) : 3200 (semée).
  await page.selectOption("#filtre-site", "1");
  const texteVentesSite1 = await page.textContent("#ventes-jour");
  verifier(
    texteVentesSite1.includes("Magasin de stock") && !texteVentesSite1.includes("Comptoir"),
    "bascule vue : « Magasin de stock » -> Comptoir disparaît de la liste des ventes"
  );
  const totalSite1 = await page.textContent("#ventes-total");
  verifier(totalSite1.includes("8") && totalSite1.includes("500"), `bascule vue : total du site Magasin correct (lu : "${totalSite1}")`);
  const texteAlertesSite1 = await page.textContent("#liste-alertes");
  verifier(texteAlertesSite1.includes("Article rare"), "bascule vue : alertes du site Magasin toujours présentes (Article rare y est)");

  await page.selectOption("#filtre-site", "2");
  const texteVentesSite2 = await page.textContent("#ventes-jour");
  verifier(
    texteVentesSite2.includes("Comptoir") && !texteVentesSite2.includes("Magasin de stock"),
    "bascule vue : « Comptoir » -> Magasin de stock disparaît de la liste des ventes"
  );
  const totalSite2 = await page.textContent("#ventes-total");
  verifier(totalSite2.includes("3") && totalSite2.includes("200"), `bascule vue : total du site Comptoir correct (lu : "${totalSite2}")`);
  const texteAlertesSite2 = await page.textContent("#liste-alertes");
  verifier(!texteAlertesSite2.includes("Article rare"), "bascule vue : alertes du site Magasin absentes en vue Comptoir (Article rare est au Magasin)");

  await page.selectOption("#filtre-site", "");
  const totalRevenuConsolide = await page.textContent("#ventes-total");
  verifier(totalRevenuConsolide.includes("11") && totalRevenuConsolide.includes("700"), "bascule vue : retour à « Les deux sites » -> total consolidé identique à avant le filtrage");

  // --- Saisie rapide (recette/dépense hors vente) : RÉELLE depuis le cycle 16 ---
  await page.click("#btn-recette");
  await page.fill("#saisie-montant", "4500");
  await page.fill("#saisie-description", "Vente de chutes de bois");
  await page.selectOption("#saisie-site", "1");
  await page.click("#saisie-valider");
  await page.waitForSelector("#zone-succes-saisie:not([hidden])", { timeout: 5000 });
  verifier(
    (await page.textContent("#zone-succes-saisie")).includes("enregistrée"),
    "responsable : saisie rapide d'une recette réellement enregistrée (POST /transactions)"
  );

  // Un agent qui tenterait cet écran est redirigé ailleurs (déjà prouvé pour
  // agent_stock plus haut) — ici on vérifie le sens inverse : le responsable
  // qui irait sur inventaire.html n'est PAS bloqué (rôle non restreint côté
  // inventaire.html qui n'autorise QUE agent_stock).
  await page.goto(`${SERVEUR_URL}/app/inventaire.html`);
  await page.waitForURL((u) => !u.pathname.endsWith("inventaire.html"), { timeout: 10000 });
  await page.waitForLoadState("networkidle");
  verifier(!page.url().endsWith("inventaire.html"), "responsable : inventaire.html réservé à l'agent stock -> redirigé");

  await page.goto(`${SERVEUR_URL}/app/tableau-bord.html`, { waitUntil: "networkidle" });
  for (const largeur of LARGEURS) {
    await page.setViewportSize({ width: largeur, height: largeur < 700 ? 780 : largeur < 1400 ? 800 : 960 });
    await mesurerEtCapturer(page, "tableau-bord", largeur);
  }
  await contexte.close();
}

// ============================================================================
// 6. Sans session -> toujours renvoyé à la connexion
// ============================================================================
{
  const { contexte, page } = await nouvellePage();
  for (const chemin of ["vente.html", "tableau-bord.html", "inventaire.html"]) {
    await page.goto(`${SERVEUR_URL}/app/${chemin}`);
    await page.waitForURL(/connexion\.html/, { timeout: 10000 });
    verifier(page.url().endsWith("connexion.html"), `sans session : ${chemin} -> redirigé vers connexion.html`);
  }
  await contexte.close();
}

// ============================================================================
// 7. Déconnexion RÉELLE : révoque le jeton côté serveur (chantier C11, cycle 21)
// ============================================================================
{
  const { contexte, page } = await nouvellePage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  const jetonAvant = await page.evaluate(() => JSON.parse(sessionStorage.getItem("qf_session")).jeton);

  const [reponseDeconnexion] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/auth/deconnexion") && r.request().method() === "POST", { timeout: 10000 }),
    page.click("#bouton-deconnexion"),
  ]);
  verifier(reponseDeconnexion.status() === 204, "déconnexion réelle : POST /auth/deconnexion -> 204");
  await page.waitForURL(/connexion\.html/, { timeout: 10000 });
  verifier(page.url().endsWith("connexion.html"), "déconnexion réelle : redirigé vers connexion.html");

  // Le jeton effacé localement était encore signature-valide et non expiré :
  // rejouer un appel avec ce MÊME jeton (intercepté avant l'effacement)
  // prouve que la révocation a bien eu lieu côté serveur, pas seulement
  // localement (sessionStorage.clear() ne suffirait pas à protéger un jeton
  // déjà volé/intercepté auparavant).
  const statutApresRevocation = await page.evaluate(async (jeton) => {
    const r = await fetch("/moi", { headers: { Authorization: "Bearer " + jeton } });
    return r.status;
  }, jetonAvant);
  verifier(statutApresRevocation === 401, `déconnexion réelle : le jeton révoqué est refusé même en le rejouant (statut ${statutApresRevocation})`);

  await contexte.close();
}

await navigateur.close();

console.log(`RÉUSSIS (${ok.length}) :`);
ok.forEach((s) => console.log("  [ok] " + s));
if (ko.length) {
  console.log(`\nÉCHECS (${ko.length}) :`);
  ko.forEach((s) => console.log("  [ECHEC] " + s));
}
console.log(`\nTotal : ${ok.length + ko.length} contrôles, ${ko.length} échec(s).`);
process.exit(ko.length ? 1 : 0);
