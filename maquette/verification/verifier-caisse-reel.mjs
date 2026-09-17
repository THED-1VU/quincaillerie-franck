/* Vérifie, PAR EXÉCUTION RÉELLE, l'écran de clôture de caisse (piste C6,
   2026-09, chantier C6, addendum point g) : maquette/cloture-caisse.html
   câble réellement server/app/routes/caisse.py.

   1. Accès réservé au responsable — agent stock et agent comptabilité
      redirigés, comme rh.html (CDC §3.5, même périmètre de sensibilité).
   2. Mise en page aux 5 largeurs habituelles.
   3. L'attendu affiché AVANT saisie correspond exactement à une vente
      réelle créée pour l'occasion (GET /caisse/attendu, jamais recalculé
      dans la page).
   4. Une clôture exacte (compté = attendu) passe sans commentaire, écart
      affiché nul.
   5. Une clôture en écart SANS commentaire est refusée par le serveur, le
      message apparaît près du formulaire (jamais un texte inventé côté
      page) ; avec un commentaire, elle passe et l'écart exact s'affiche.
   6. La clôture réapparaît dans l'historique après création.

   Prérequis : serveur démarré sur SERVEUR_URL, servant /app.
   Réinitialise elle-même la base (jeu d'essai + mots de passe réels).
*/
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE_DEPOT = resolve(ICI, "..", "..");

const SERVEUR_URL = process.env.SERVEUR_URL || "http://127.0.0.1:8010";
// PGDATABASE_PISTE / PGDEV_RACINE (travail en parallèle, RAPPORT AVANCEMENT/
// TRAVAIL_PARALLELE.md) : chaque piste rejoue ce script sur SA PROPRE base
// (jamais quincaillerie_test) sans modifier les scripts communs aux trois.
const PGDEV = resolve(process.env.PGDEV_RACINE || RACINE_DEPOT, "_pgdev");
const PSQL = resolve(PGDEV, "pgsql", "bin", "psql.exe");
const BASE_DB = process.env.PGDATABASE_PISTE || "quincaillerie_test";

const MDP_RESPONSABLE = "ResponsableTest123";
const MDP_AGENT_STOCK = "AgentStockTest123";
const MDP_AGENT_COMPTA = "AgentComptaTest123";
const MDP_AGENT_COMPTA_COMPTOIR = "AgentComptaCptTest123";

const ok = [], ko = [];
const verifier = (cond, libelle) => (cond ? ok : ko).push(libelle);

function psql(sql) {
  execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", BASE_DB, "-q", "-c", sql,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
}

function psqlValeur(sql) {
  return execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", BASE_DB, "-t", "-A", "-q", "-c", sql,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" }, encoding: "utf-8" }).trim();
}

console.log("== Préparation de la base (jeu d'essai + comptes de test) ==");
execFileSync(PSQL, [
  "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", BASE_DB,
  "-v", "ON_ERROR_STOP=1", "-q", "-f", resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"),
], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA_COMPTOIR}', gen_salt('bf', 12)) WHERE identifiant='comptoir.compta';`);
console.log("Base prête.\n");

// --- Deux ventes réelles, une par site, pour avoir un attendu non nul aux
// deux sites (Magasin = clôture exacte, Comptoir = clôture en écart). ---
async function connexionApi(identifiant, motDePasse) {
  const r = await fetch(`${SERVEUR_URL}/auth/connexion`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifiant, mot_de_passe: motDePasse }),
  });
  const corps = await r.json();
  if (!corps.jeton) throw new Error("Connexion API échouée pour " + identifiant + " : " + JSON.stringify(corps));
  return corps.jeton;
}

async function creerVente(jeton, articleId, prixUnitaire) {
  const r = await fetch(`${SERVEUR_URL}/ventes`, {
    method: "POST",
    headers: { Authorization: `Bearer ${jeton}`, "Content-Type": "application/json" },
    body: JSON.stringify({ mode_paiement: "especes", lignes: [{ article_id: articleId, quantite: 1, prix_unitaire: prixUnitaire }] }),
  });
  const corps = await r.json();
  if (!r.ok) throw new Error("Création de vente échouée : " + JSON.stringify(corps));
  return corps;
}

// Article 1 (Ciment) appartient au Magasin (site 1), article 3 (Clou) au
// Comptoir (site 2) — voir db/tests/00_jeu_essai.sql.
const jetonComptaMagasin = await connexionApi("magasin.compta", MDP_AGENT_COMPTA);
const venteMagasin = await creerVente(jetonComptaMagasin, 1, 6500);
const jourMagasin = psqlValeur(`SELECT date_encaissement::date FROM ventes WHERE id = ${venteMagasin.vente_id};`);

const jetonComptaComptoir = await connexionApi("comptoir.compta", MDP_AGENT_COMPTA_COMPTOIR);
const venteComptoir = await creerVente(jetonComptaComptoir, 3, 3200);
const jourComptoir = psqlValeur(`SELECT date_encaissement::date FROM ventes WHERE id = ${venteComptoir.vente_id};`);

console.log(`Vente Magasin (site 1) : ${venteMagasin.total_ttc} FCFA le ${jourMagasin}`);
console.log(`Vente Comptoir (site 2) : ${venteComptoir.total_ttc} FCFA le ${jourComptoir}\n`);

const navigateur = await chromium.launch({ channel: "chrome" });
const CAPTURES = resolve(ICI, "..", "captures") + "/";

async function mesurerMiseEnPage(page, nomEcran, largeur) {
  const metriques = await page.evaluate(() => {
    const de = document.documentElement;
    const cibles = [...document.querySelectorAll("button, a, input, select")]
      .map((el) => Math.round(el.getBoundingClientRect().height)).filter((h) => h > 0);
    return {
      overflowH: de.scrollWidth > de.clientWidth + 1,
      cibleMin: cibles.length ? Math.min(...cibles) : null,
    };
  });
  await page.screenshot({ path: `${CAPTURES}${nomEcran}-${largeur}.png`, fullPage: true });
  verifier(!metriques.overflowH, `${nomEcran}@${largeur} : aucun débordement horizontal`);
  if (metriques.cibleMin !== null) {
    verifier(largeur > 768 || metriques.cibleMin >= 44, `${nomEcran}@${largeur} : cible tactile mini ${metriques.cibleMin}px ≥ 44px`);
  }
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

// ============================================================================
// 1. Accès réservé au responsable
// ============================================================================
{
  for (const [identifiant, mdp] of [
    ["magasin.stock", MDP_AGENT_STOCK],
    ["magasin.compta", MDP_AGENT_COMPTA],
  ]) {
    const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
    const page = await contexte.newPage();
    await seConnecter(page, identifiant, mdp);
    await page.goto(`${SERVEUR_URL}/app/cloture-caisse.html`, { waitUntil: "networkidle" });
    verifier(!page.url().endsWith("cloture-caisse.html"), `${identifiant} : accès direct à cloture-caisse.html -> reredirigé`);
    await contexte.close();
  }
}

// ============================================================================
// 2. Mise en page aux 5 largeurs habituelles, avec un responsable connecté
// ============================================================================
for (const largeur of [360, 390, 768, 1366, 1920]) {
  const contexte = await navigateur.newContext({
    viewport: { width: largeur, height: largeur < 700 ? 900 : largeur < 1400 ? 900 : 1000 },
  });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/cloture-caisse.html`, { waitUntil: "networkidle" });
  await mesurerMiseEnPage(page, "cloture-caisse", largeur);
  await contexte.close();
}

// ============================================================================
// 3-6. Flux réel : attendu affiché, clôture exacte, clôture en écart refusée
//      sans commentaire puis acceptée avec, historique mis à jour.
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 1000 } });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/cloture-caisse.html`, { waitUntil: "networkidle" });
  verifier(page.url().endsWith("cloture-caisse.html"), "responsable : accès à cloture-caisse.html");

  // --- Site Magasin, clôture EXACTE (compté = attendu) ---
  await page.selectOption("#f-site", "1");
  const [reponseAttendu] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/caisse/attendu") && r.request().method() === "GET", { timeout: 10000 }),
    page.fill("#f-date", jourMagasin),
  ]);
  const corpsAttendu = await reponseAttendu.json();
  verifier(reponseAttendu.ok(), "attendu réel : GET /caisse/attendu -> 200");
  verifier(corpsAttendu.attendu_especes === venteMagasin.total_ttc,
    `attendu réel : espèces attendues = ${corpsAttendu.attendu_especes} (vente réelle = ${venteMagasin.total_ttc})`);
  await page.waitForFunction(() => document.getElementById("bloc-attendu").hidden === false, { timeout: 10000 });
  const texteAttendu = (await page.locator("#liste-attendu").textContent()) || "";
  // fcfa() insère un séparateur de milliers (espace) — on compare les
  // chiffres seuls pour ne pas dépendre du caractère exact utilisé.
  const chiffresAttendus = String(Math.round(venteMagasin.total_ttc));
  verifier(
    texteAttendu.replace(/\s| /g, "").includes(chiffresAttendus),
    "attendu réel : le montant attendu s'affiche à l'écran AVANT toute saisie du comptage"
  );

  await page.fill("#f-especes", String(venteMagasin.total_ttc));
  const [reponseClotureExacte] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/caisse") && r.request().method() === "POST", { timeout: 10000 }),
    page.click("#bouton-cloturer"),
  ]);
  verifier(reponseClotureExacte.ok(), "clôture exacte réelle : POST /caisse -> 201");
  const corpsClotureExacte = await reponseClotureExacte.json();
  verifier(corpsClotureExacte.ecart_especes === 0, "clôture exacte réelle : écart calculé par le serveur = 0");
  await page.waitForFunction(() => document.getElementById("zone-succes-cloture").hidden === false, { timeout: 10000 });
  verifier(true, "clôture exacte réelle : message de succès affiché");

  // --- Site Comptoir, écart SANS commentaire -> refusé, message affiché ---
  await page.selectOption("#f-site", "2");
  await page.fill("#f-date", jourComptoir);
  await page.waitForResponse((r) => r.url().includes("/caisse/attendu"), { timeout: 10000 });
  await page.fill("#f-especes", String(venteComptoir.total_ttc - 200));
  const [reponseRefusee] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/caisse") && r.request().method() === "POST", { timeout: 10000 }),
    page.click("#bouton-cloturer"),
  ]);
  verifier(reponseRefusee.status() === 422, "clôture en écart réelle SANS commentaire : POST /caisse -> 422 (refusé par le serveur)");
  await page.waitForFunction(() => document.getElementById("zone-erreur-cloture").hidden === false, { timeout: 10000 });
  const messageErreur = await page.locator("#zone-erreur-cloture").textContent();
  verifier(/commentaire/i.test(messageErreur || ""), "clôture en écart réelle : message d'erreur du SERVEUR affiché près du formulaire, en français (" + messageErreur + ")");

  // --- Même site/jour, AVEC commentaire cette fois -> accepté ---
  await page.fill("#f-commentaire", "200 FCFA manquants, à vérifier avec le vendeur.");
  const [reponseAcceptee] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/caisse") && r.request().method() === "POST", { timeout: 10000 }),
    page.click("#bouton-cloturer"),
  ]);
  verifier(reponseAcceptee.ok(), "clôture en écart réelle AVEC commentaire : POST /caisse -> 201");
  const corpsAcceptee = await reponseAcceptee.json();
  verifier(corpsAcceptee.ecart_especes === -200, `clôture en écart réelle : écart calculé par le serveur = ${corpsAcceptee.ecart_especes} (attendu -200)`);

  // --- Historique mis à jour ---
  await page.waitForFunction(
    (id) => document.getElementById("liste-clotures").textContent.includes("n°" + id),
    corpsAcceptee.cloture_id, { timeout: 10000 }
  );
  verifier(true, "historique réel : la clôture créée réapparaît dans la liste après création");

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
