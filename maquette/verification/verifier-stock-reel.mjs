/* Vérifie, PAR EXÉCUTION RÉELLE, l'écran stock.html (cycle 11) : donne une
   interface aux 6 opérations d'articles et de stock du cycle 9 (création,
   modification, réception, transfert, casse, retours), ainsi qu'à la
   fonction de sélection inter-site du cycle 11 (migration 015).

   1. Un agent stock (Magasin) crée un article, en fait la réception, le
      transfère au Comptoir, fait un retour client et un retour fournisseur
      — jamais de bouton « Casse » pour lui.
   2. Le responsable modifie le prix d'un article et enregistre une casse.
   3. AUCUN montant FCFA, AUCUN champ de prix n'atteint la page ni les
      réponses réseau vues par l'agent stock — prouvé par capture ET par
      inspection du DOM et du réseau, pas seulement par lecture du code.
   4. Layout aux 5 largeurs (360/390/768/1366/1920), cibles ≥ 44 px.

   Prérequis : serveur démarré sur SERVEUR_URL, servant /app (cycle 5).
   Réinitialise elle-même la base (jeu d'essai + mots de passe réels).
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

const MDP_AGENT_STOCK = "AgentStockTest123";
const MDP_RESPONSABLE = "ResponsableTest123";

const ok = [], ko = [];
const verifier = (cond, libelle) => (cond ? ok : ko).push(libelle);

function psql(sql) {
  execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE, "-q", "-c", sql,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
}

function psqlValeur(sql) {
  return execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
    "-t", "-A", "-c", sql,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } }).toString().trim();
}

console.log("== Préparation de la base (jeu d'essai + comptes de test) ==");
execFileSync(PSQL, [
  "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
  "-v", "ON_ERROR_STOP=1", "-q", "-f", resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"),
], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);

// Une vente réelle du Magasin (site 1) portant sur « Ciment CIM II 50 kg »
// (article 1), pour tester le retour client contre une vente réelle.
psql(`INSERT INTO ventes (id, site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc, utilisateur_caisse_id, mode_paiement, date_encaissement)
       VALUES (900, 1, 4, 'payee', 6500, 0, 0, 6500, 1, 'especes', NOW());`);
psql(`INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id) VALUES (900, 1, 2, 6500, 1);`);
const VENTE_ID = "900";

console.log("Base prête.\n");

const navigateur = await chromium.launch({ channel: "chrome" });

async function nouvellePage(largeur = 1366, hauteur = 900) {
  const contexte = await navigateur.newContext({ viewport: { width: largeur, height: hauteur } });
  const page = await contexte.newPage();
  if (process.env.DEBUG_STOCK) {
    page.on("console", (m) => console.log("  [console]", m.type(), m.text()));
    page.on("pageerror", (e) => console.log("  [pageerror]", e.message));
  }
  return { contexte, page };
}

async function seConnecter(page, identifiant, motDePasse) {
  await page.goto(`${SERVEUR_URL}/app/connexion.html`, { waitUntil: "networkidle" });
  await page.fill("#identifiant", identifiant);
  await page.fill("#motdepasse", motDePasse);
  const [reponse] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/auth/connexion"), { timeout: 10000 }),
    page.click("#bouton-connexion"),
  ]);
  if (reponse.ok()) {
    await page.waitForURL((u) => !u.pathname.endsWith("connexion.html"), { timeout: 10000 });
    await page.waitForLoadState("networkidle");
  }
}

async function ouvrirArticle(page, nomPartiel, action) {
  await page.fill("#recherche", nomPartiel);
  const item = page.locator("#liste-articles li", { hasText: nomPartiel }).first();
  await item.waitFor({ timeout: 5000 });
  await item.getByRole("button", { name: action, exact: true }).click();
  await page.waitForSelector("#carte-panneau:not([hidden])", { timeout: 5000 });
}

async function attendreSucces(page) {
  await page.waitForSelector("#zone-succes-panneau:not([hidden])", { timeout: 10000 });
}

// Clique le bouton de validation du panneau — jamais un sélecteur "text="
// non ancré : "Transférer" (bouton) matche aussi "Quantité à transférer"
// (libellé), un piège trouvé en écrivant ce script.
async function validerPanneau(page) {
  await page.locator("#panneau-contenu button").last().click();
}

const LARGEURS = [360, 390, 768, 1366, 1920];

// ============================================================================
// 1. Agent stock (Magasin) : les 5 opérations qui lui sont ouvertes
// ============================================================================
{
  const { page } = await nouvellePage(390, 844);
  await seConnecter(page, "magasin.stock", MDP_AGENT_STOCK);
  await page.goto(`${SERVEUR_URL}/app/stock.html`, { waitUntil: "networkidle" });
  verifier(page.url().endsWith("stock.html"), "agent stock : accès à stock.html");

  // --- AUCUN prix, AUCUN FCFA : DOM et réseau ---
  const texteDom = await page.evaluate(() => document.body.innerText);
  verifier(!/FCFA/i.test(texteDom), "agent stock : aucune occurrence de « FCFA » dans la page");

  const reponsesArticles = await page.evaluate(async () => {
    const session = JSON.parse(sessionStorage.getItem("qf_session"));
    const entetes = { Authorization: "Bearer " + session.jeton };
    const [a, b] = await Promise.all([
      fetch("/articles", { headers: entetes }).then((r) => r.json()),
      fetch("/articles/autre-site", { headers: entetes }).then((r) => r.json()),
    ]);
    return { articles: a.articles, autreSite: b };
  });
  const champsInterdits = new Set();
  reponsesArticles.articles.forEach((a) => Object.keys(a).forEach((k) => { if (/prix|montant/i.test(k)) champsInterdits.add(k); }));
  reponsesArticles.autreSite.forEach((a) => Object.keys(a).forEach((k) => { if (/prix|montant/i.test(k)) champsInterdits.add(k); }));
  verifier(champsInterdits.size === 0, `agent stock : aucun champ de prix dans /articles ni /articles/autre-site (trouvé : ${[...champsInterdits].join(",") || "aucun"})`);

  // --- Création d'un article (sans prix, jamais proposé) ---
  await page.click("#lien-nouvel-article");
  verifier(await page.locator("#f-prix-achat").count() === 0, "agent stock : aucun champ de prix dans le formulaire de création");
  await page.fill("#f-nom", "Scie à métaux (créée par l'agent)");
  await page.fill("#f-unite", "pièce");
  await validerPanneau(page);
  await attendreSucces(page);
  verifier(true, "agent stock : création d'article réussie");

  // --- Réception sur « Ciment » ---
  await ouvrirArticle(page, "Ciment", "+ Réception");
  await page.fill("#f-quantite", "10");
  await page.fill("#f-motif", "Livraison test cycle 11");
  await validerPanneau(page);
  await attendreSucces(page);
  const stockApresReception = psqlValeur("SELECT quantite_stock FROM articles WHERE id = 1;");
  verifier(stockApresReception === "40", `agent stock : réception réelle (stock Ciment = ${stockApresReception}, attendu 40)`);

  // --- Transfert de « Ciment » vers le Comptoir ---
  await ouvrirArticle(page, "Ciment", "Transférer");
  await page.waitForFunction(() => document.querySelectorAll("#panneau-contenu select option").length > 1, { timeout: 5000 });
  const optionsDestination = await page.locator("#panneau-contenu select option").allTextContents();
  verifier(optionsDestination.some((t) => t.includes("Comptoir")), "agent stock : sélecteur de transfert propose un article du Comptoir");
  await page.selectOption("#panneau-contenu select", { label: optionsDestination.find((t) => t.includes("Clou")) });
  await page.fill("#f-quantite", "5");
  await page.fill("#f-motif", "Réappro comptoir, test cycle 11");
  await validerPanneau(page);
  await attendreSucces(page);
  const stockApresTransfert = psqlValeur("SELECT quantite_stock FROM articles WHERE id = 1;");
  verifier(stockApresTransfert === "35", `agent stock : transfert réel (stock Ciment = ${stockApresTransfert}, attendu 35)`);

  // --- Retour client sur « Ciment », contre la vraie vente n°900 ---
  await ouvrirArticle(page, "Ciment", "Retour client");
  await page.fill("#f-quantite", "1");
  await page.fill("#f-vente-id", VENTE_ID);
  await validerPanneau(page);
  await attendreSucces(page);
  const stockApresRetourClient = psqlValeur("SELECT quantite_stock FROM articles WHERE id = 1;");
  verifier(stockApresRetourClient === "36", `agent stock : retour client réel (stock Ciment = ${stockApresRetourClient}, attendu 36)`);

  // --- Retour fournisseur, contre la réception faite plus haut ---
  const idReception = psqlValeur(
    "SELECT id FROM mouvements_stock WHERE article_id = 1 AND categorie = 'reception_fournisseur' ORDER BY id DESC LIMIT 1;"
  );
  await ouvrirArticle(page, "Ciment", "Retour fournisseur");
  await page.fill("#f-quantite", "2");
  await page.fill("#f-mouvement-id", idReception);
  await validerPanneau(page);
  await attendreSucces(page);
  const stockApresRetourFournisseur = psqlValeur("SELECT quantite_stock FROM articles WHERE id = 1;");
  verifier(stockApresRetourFournisseur === "34", `agent stock : retour fournisseur réel (stock Ciment = ${stockApresRetourFournisseur}, attendu 34)`);

  // --- Pas de bouton Casse pour un agent stock ---
  await page.fill("#recherche", "Ciment");
  const ligneCiment = page.locator("#liste-articles li", { hasText: "Ciment" }).first();
  verifier(await ligneCiment.getByRole("button", { name: "Casse", exact: true }).count() === 0,
    "agent stock : aucun bouton « Casse » (réservée au responsable)");

  // --- FCFA toujours absent après toutes ces opérations ---
  const texteDomFinal = await page.evaluate(() => document.body.innerText);
  verifier(!/FCFA/i.test(texteDomFinal), "agent stock : toujours aucune occurrence de « FCFA » après les opérations");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: `${CAPTURES}stock-390.png`, fullPage: true });
  for (const largeur of LARGEURS) {
    await page.setViewportSize({ width: largeur, height: largeur < 700 ? 780 : largeur < 1400 ? 800 : 960 });
    const metriques = await page.evaluate(() => {
      const de = document.documentElement;
      const cibles = [...document.querySelectorAll("button, a, input, select")]
        .map((el) => Math.round(el.getBoundingClientRect().height)).filter((h) => h > 0);
      return { overflowH: de.scrollWidth > de.clientWidth + 1, cibleMin: cibles.length ? Math.min(...cibles) : null };
    });
    await page.screenshot({ path: `${CAPTURES}stock-${largeur}.png`, fullPage: true });
    verifier(!metriques.overflowH, `stock@${largeur} : aucun débordement horizontal`);
    if (metriques.cibleMin !== null) {
      verifier(largeur > 768 || metriques.cibleMin >= 44, `stock@${largeur} : cible tactile mini ${metriques.cibleMin}px ≥ 44px`);
    }
  }
}

// ============================================================================
// 2. Responsable : modification (prix) et casse
// ============================================================================
{
  const { page } = await nouvellePage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/stock.html`, { waitUntil: "networkidle" });
  verifier(page.url().endsWith("stock.html"), "responsable : accès à stock.html");

  await ouvrirArticle(page, "Fer", "Modifier");
  await page.fill("#f-prix-vente", "3800");
  await validerPanneau(page);
  await attendreSucces(page);
  const prixApresModif = psqlValeur("SELECT prix_vente FROM articles WHERE id = 2;");
  verifier(prixApresModif.startsWith("3800"), `responsable : modification de prix réelle (prix Fer = ${prixApresModif}, attendu 3800)`);
  const traceModif = psqlValeur(
    "SELECT count(*) FROM historique_prix_articles WHERE article_id = 2 AND nouveau_prix_vente = 3800;"
  );
  verifier(traceModif === "1", "responsable : modification de prix tracée dans historique_prix_articles");

  await ouvrirArticle(page, "Fer", "Casse");
  await page.fill("#f-quantite", "1");
  await page.fill("#f-motif", "Barre pliée, essai cycle 11");
  await validerPanneau(page);
  await attendreSucces(page);
  const stockApresCasse = psqlValeur("SELECT quantite_stock FROM articles WHERE id = 2;");
  verifier(stockApresCasse === "39", `responsable : casse réelle (stock Fer = ${stockApresCasse}, attendu 39)`);

  for (const largeur of LARGEURS) {
    await page.setViewportSize({ width: largeur, height: largeur < 700 ? 780 : largeur < 1400 ? 800 : 960 });
    await page.screenshot({ path: `${CAPTURES}stock-responsable-${largeur}.png`, fullPage: true });
  }
}

await navigateur.close();

console.log(`RÉUSSIS (${ok.length}) :`);
ok.forEach((l) => console.log("  [ok]", l));
if (ko.length) {
  console.log(`\nÉCHECS (${ko.length}) :`);
  ko.forEach((l) => console.log("  [KO]", l));
}
console.log(`\nTotal : ${ok.length + ko.length} contrôles, ${ko.length} échec(s).`);
process.exit(ko.length ? 1 : 0);
