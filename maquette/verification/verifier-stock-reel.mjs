/* Vérifie, PAR EXÉCUTION RÉELLE, l'écran stock.html (cycle 11) ET l'écran
   declarations.html (chantier A, point f) : création, modification,
   réception, transfert, retour fournisseur — et, depuis le sous-chantier 2
   (point f, migration 036), les DÉCLARATIONS de casse et de retour client
   (aucun effet sur le stock tant que le responsable ne valide pas sur
   declarations.html), plus la validation d'un article offert.

   RÉÉCRIT AU CYCLE 51 (chantier C13, 2026-09-25) : l'ancienne version
   testait la casse et le retour client à un seul temps (stock décrémenté
   immédiatement) et affirmait que l'agent stock n'a pas de bouton « Casse »
   — les trois contredisaient le comportement livré par le point f et le
   chantier A ; la suite était rouge sans que personne ne le voie (la CI
   n'exécute que pytest).

   1. Un agent stock (Magasin) crée un article, en fait la réception, le
      transfère au Comptoir, DÉCLARE un retour client (issue + état) et une
      casse, fait un retour fournisseur — le stock ne bouge que pour la
      réception, le transfert et le retour fournisseur.
   2. Le responsable modifie le prix d'un article, puis valide sur
      declarations.html : la casse (décrémente), le retour client revendable
      (réintègre) et un article offert (décrémente) — effets vérifiés en
      base à chaque étape.
   3. AUCUN montant FCFA, AUCUN champ de prix n'atteint la page ni les
      réponses réseau vues par l'agent stock.
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

// Stock du Ciment (article 1) au Magasin (site 1).
function stockCiment() {
  return Number(psqlValeur("SELECT quantite_stock FROM stocks_sites WHERE article_id = 1 AND site_id = 1;"));
}

// Nombre de déclarations EN ATTENTE d'une table de déclaration.
function nbEnAttente(table) {
  return psqlValeur(`SELECT count(*) FROM ${table} WHERE statut = 'en_attente';`);
}

console.log("== Préparation de la base (jeu d'essai + comptes de test) ==");
execFileSync(PSQL, [
  "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
  "-v", "ON_ERROR_STOP=1", "-q", "-f", resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"),
], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);

// Une vente réelle du Magasin (site 1) portant sur « Ciment CIM II 50 kg »
// (article 1), pour tester la déclaration de retour client contre une vente.
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
// 1. Agent stock (Magasin) : opérations ouvertes + DÉCLARATIONS sans effet
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
    const a = await fetch("/articles", { headers: entetes }).then((r) => r.json());
    return { articles: a.articles };
  });
  const champsInterdits = new Set();
  reponsesArticles.articles.forEach((a) => Object.keys(a).forEach((k) => { if (/prix|montant/i.test(k)) champsInterdits.add(k); }));
  verifier(champsInterdits.size === 0, `agent stock : aucun champ de prix dans /articles (trouvé : ${[...champsInterdits].join(",") || "aucun"})`);

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
  await page.fill("#f-motif", "Livraison test cycle 51");
  await validerPanneau(page);
  await attendreSucces(page);
  verifier(stockCiment() === 40, `agent stock : réception réelle (stock Ciment = ${stockCiment()}, attendu 40)`);

  // --- Transfert de « Ciment » vers le Comptoir ---
  await ouvrirArticle(page, "Ciment", "Transférer");
  await page.waitForFunction(() => document.querySelectorAll("#panneau-contenu select option").length > 1, { timeout: 5000 });
  const optionsDestination = await page.locator("#panneau-contenu select option").allTextContents();
  verifier(optionsDestination.some((t) => t.includes("Comptoir")), "agent stock : sélecteur de transfert propose le site de destination Comptoir");
  await page.selectOption("#panneau-contenu select", { label: optionsDestination.find((t) => t.includes("Comptoir")) });
  await page.fill("#f-quantite", "5");
  await page.fill("#f-motif", "Réappro comptoir, test cycle 51");
  await validerPanneau(page);
  await attendreSucces(page);
  verifier(stockCiment() === 35, `agent stock : transfert réel (stock Ciment = ${stockCiment()}, attendu 35)`);

  // --- DÉCLARATION de retour client sur « Ciment », contre la vente n°900 ---
  // Sous-chantier 2 (point f) : déclaration SANS effet sur le stock.
  await ouvrirArticle(page, "Ciment", "Retour client");
  await page.fill("#f-quantite", "1");
  await page.fill("#f-vente-id", VENTE_ID);
  await page.selectOption("#f-issue", "echange");
  await page.selectOption("#f-etat", "revendable");
  await validerPanneau(page);
  await attendreSucces(page);
  verifier(stockCiment() === 35, `agent stock : déclaration de retour client SANS effet stock (stock Ciment = ${stockCiment()}, attendu 35)`);
  verifier(nbEnAttente("declarations_retour_client") === "1", "agent stock : la déclaration de retour client est en attente en base");

  // --- Retour fournisseur, contre la réception faite plus haut ---
  const idReception = psqlValeur(
    "SELECT id FROM mouvements_stock WHERE article_id = 1 AND categorie = 'reception_fournisseur' ORDER BY id DESC LIMIT 1;"
  );
  await ouvrirArticle(page, "Ciment", "Retour fournisseur");
  await page.fill("#f-quantite", "2");
  await page.fill("#f-mouvement-id", idReception);
  await validerPanneau(page);
  await attendreSucces(page);
  verifier(stockCiment() === 33, `agent stock : retour fournisseur réel (stock Ciment = ${stockCiment()}, attendu 33)`);

  // --- DÉCLARATION de casse par l'agent stock (ouverte depuis le
  // sous-chantier 2), sans effet sur le stock ---
  await ouvrirArticle(page, "Ciment", "Casse");
  await page.fill("#f-quantite", "1");
  await page.fill("#f-motif", "Sac déchiré, essai cycle 51");
  await validerPanneau(page);
  await attendreSucces(page);
  verifier(stockCiment() === 33, `agent stock : déclaration de casse SANS effet stock (stock Ciment = ${stockCiment()}, attendu 33)`);
  verifier(nbEnAttente("declarations_casse") === "1", "agent stock : la déclaration de casse est en attente en base");

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
// 2. Responsable : modification de prix, puis validation des déclarations
//    sur declarations.html (casse -> décrémente, retour revendable ->
//    réintègre, article offert -> décrémente)
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

  // --- Déclaration d'un article offert (créée ici par l'API : la
  // déclaration n'a pas encore d'écran dédié côté vente) ---
  const declarationOfferte = await page.evaluate(async () => {
    const session = JSON.parse(sessionStorage.getItem("qf_session"));
    const reponse = await fetch("/stock/articles-offerts/declarations", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + session.jeton },
      body: JSON.stringify({
        article_id: 1, site_id: 1, quantite: 1,
        motif: "Geste commercial, essai cycle 51", employe_id: 1,
      }),
    });
    return { statut: reponse.status, corps: await reponse.json() };
  });
  verifier(declarationOfferte.statut === 201, "responsable : déclaration d'article offert créée (API)");

  // --- declarations.html : la casse en attente est validée et décrémente ---
  await page.goto(`${SERVEUR_URL}/app/declarations.html`, { waitUntil: "networkidle" });
  verifier(page.url().endsWith("declarations.html"), "responsable : accès à declarations.html");
  const ligneCasse = page.locator("#liste-casse li", { hasText: "Ciment" }).first();
  verifier(await ligneCasse.count() > 0, "declarations : la casse déclarée par l'agent apparaît en attente");
  const [reponseValidationCasse] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/stock/casse/declarations/") && r.request().method() === "POST", { timeout: 10000 }),
    ligneCasse.getByRole("button", { name: "Valider" }).click(),
  ]);
  verifier(reponseValidationCasse.ok(), "declarations : validation de la casse acceptée par le serveur");
  await page.waitForFunction(() => document.querySelectorAll("#liste-casse li").length === 1, { timeout: 5000 });
  verifier(stockCiment() === 32, `responsable : validation de la casse décrémente réellement (stock Ciment = ${stockCiment()}, attendu 32)`);

  // --- declarations.html : retour client revendable validé -> réintègre ---
  const ligneRetour = page.locator("#liste-retours li", { hasText: "vente n°900" }).first();
  verifier(await ligneRetour.count() > 0, "declarations : le retour client déclaré par l'agent apparaît en attente");
  const [reponseValidationRetour] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/stock/retours-client/declarations/") && r.request().method() === "POST", { timeout: 10000 }),
    ligneRetour.getByRole("button", { name: "Valider" }).click(),
  ]);
  verifier(reponseValidationRetour.ok(), "declarations : validation du retour client acceptée par le serveur");
  await page.waitForFunction(() => document.querySelectorAll("#liste-retours li").length === 1, { timeout: 5000 });
  verifier(stockCiment() === 33, `responsable : retour revendable réintégré (stock Ciment = ${stockCiment()}, attendu 33)`);

  // --- declarations.html : article offert validé -> décrémente ---
  const ligneOffert = page.locator("#liste-offerts li", { hasText: "Fer" }).first();
  verifier(await ligneOffert.count() > 0, "declarations : l'article offert déclaré apparaît en attente");
  const [reponseValidationOffert] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/stock/articles-offerts/declarations/") && r.request().method() === "POST", { timeout: 10000 }),
    ligneOffert.getByRole("button", { name: "Valider" }).click(),
  ]);
  verifier(reponseValidationOffert.ok(), "declarations : validation de l'article offert acceptée par le serveur");
  await page.waitForFunction(() => document.querySelectorAll("#liste-offerts li").length === 1, { timeout: 5000 });
  verifier(stockCiment() === 32, `responsable : article offert décrémenté (stock Ciment = ${stockCiment()}, attendu 32)`);

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
