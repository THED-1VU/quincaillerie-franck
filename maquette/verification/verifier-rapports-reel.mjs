/* Vérifie, PAR EXÉCUTION RÉELLE, l'écran rapports.html (cycle 12) :
   historique des comptages et exports Excel/PDF du chantier C8, réels et
   testés au niveau API depuis le cycle 10 (server/tests/test_rapports.py),
   mais sans aucune interface jusqu'à ce cycle.

   1. Le responsable voit les 3 sections (historique, export articles,
      export ventes) ; l'historique affiche un comptage réellement fait
      aujourd'hui, et rien sur une période passée.
   2. L'agent stock ne voit QUE l'export du catalogue (jamais l'historique
      ni l'export des ventes) — aucune occurrence de FCFA sur l'écran.
   3. L'agent comptabilité voit l'export du catalogue et des ventes, jamais
      l'historique (réservé au responsable).
   4. Un clic sur un bouton d'export déclenche un VRAI téléchargement de
      navigateur (pas un lien nu) — fichier non vide, dont les premiers
      octets correspondent au format annoncé (« PK » pour un .xlsx, qui
      est une archive Zip ; « %PDF » pour un .pdf).

   Prérequis : serveur démarré sur SERVEUR_URL, servant /app (cycle 5).
   Réinitialise elle-même la base (jeu d'essai + mots de passe réels).
*/
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
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
const MDP_AGENT_COMPTA = "AgentComptaTest123";
const MDP_RESPONSABLE = "ResponsableTest123";

const ok = [], ko = [];
const verifier = (cond, libelle) => (cond ? ok : ko).push(libelle);

function psql(sql) {
  execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE, "-q", "-c", sql,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
}

console.log("== Préparation de la base (jeu d'essai + comptes de test) ==");
execFileSync(PSQL, [
  "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
  "-v", "ON_ERROR_STOP=1", "-q", "-f", resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"),
], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);

// Un comptage réel d'aujourd'hui sur « Ciment CIM II 50 kg » (article 1,
// stock 30) : compté à 28, écart -2 — pour prouver que l'historique affiche
// un vrai écart, pas seulement une ligne « conforme ».
psql(`INSERT INTO comptages_stock (article_id, utilisateur_id, moment, quantite_comptee) VALUES (1, 2, 'matin', 28);`);

console.log("Base prête.\n");

const navigateur = await chromium.launch({ channel: "chrome" });

async function nouvellePage(largeur = 1366, hauteur = 900) {
  const contexte = await navigateur.newContext({ viewport: { width: largeur, height: hauteur }, acceptDownloads: true });
  const page = await contexte.newPage();
  if (process.env.DEBUG_RAPPORTS) {
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

// Clique un bouton d'export, intercepte le VRAI téléchargement de
// navigateur qui en résulte, et renvoie les premiers octets du fichier
// obtenu — jamais une simple vérification du code HTTP.
async function telechargerEtLireEntete(page, idBouton, longueur = 4) {
  const [telechargement] = await Promise.all([
    page.waitForEvent("download", { timeout: 10000 }),
    page.click(idBouton),
  ]);
  const chemin = await telechargement.path();
  const octets = readFileSync(chemin);
  return octets.subarray(0, longueur).toString("latin1");
}

const LARGEURS = [360, 390, 768, 1366, 1920];

// ============================================================================
// 1. Responsable : les 3 sections, historique réel, exports réels
// ============================================================================
{
  const { page } = await nouvellePage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/rapports.html`, { waitUntil: "networkidle" });
  verifier(page.url().endsWith("rapports.html"), "responsable : accès à rapports.html");

  for (const id of ["carte-historique", "carte-export-articles", "carte-export-ventes"]) {
    verifier(await page.isVisible(`#${id}`), `responsable : section #${id} visible`);
  }

  // Historique : la période par défaut est aujourd'hui -> le comptage semé plus haut apparaît.
  await page.waitForSelector("#liste-historique li", { timeout: 5000 });
  const texteHistorique = await page.textContent("#liste-historique");
  verifier(texteHistorique.includes("Ciment"), "responsable : historique affiche le comptage réel du jour");
  verifier(texteHistorique.includes("-2") || texteHistorique.includes("écart"), "responsable : écart réel affiché (-2)");

  // Période passée -> liste vide.
  await page.fill("#hist-debut", "2000-01-01");
  await page.fill("#hist-fin", "2000-01-02");
  await page.click("#hist-chercher");
  await page.waitForFunction(
    () => document.getElementById("liste-historique").textContent.includes("Aucun comptage"),
    { timeout: 5000 }
  );
  verifier(true, "responsable : période passée -> aucun comptage affiché");

  const enteteXlsx = await telechargerEtLireEntete(page, "#export-articles-xlsx");
  verifier(enteteXlsx.startsWith("PK"), `responsable : export articles .xlsx réellement téléchargé (en-tête « ${enteteXlsx}» )`);

  const entetePdf = await telechargerEtLireEntete(page, "#export-articles-pdf");
  verifier(entetePdf.startsWith("%PDF"), `responsable : export articles .pdf réellement téléchargé (en-tête « ${entetePdf}» )`);

  const enteteVentesXlsx = await telechargerEtLireEntete(page, "#export-ventes-xlsx");
  verifier(enteteVentesXlsx.startsWith("PK"), "responsable : export ventes .xlsx réellement téléchargé");

  for (const largeur of LARGEURS) {
    await page.setViewportSize({ width: largeur, height: largeur < 700 ? 900 : largeur < 1400 ? 900 : 1000 });
    const metriques = await page.evaluate(() => {
      const de = document.documentElement;
      const cibles = [...document.querySelectorAll("button, a, input, select")]
        .map((el) => Math.round(el.getBoundingClientRect().height)).filter((h) => h > 0);
      return { overflowH: de.scrollWidth > de.clientWidth + 1, cibleMin: cibles.length ? Math.min(...cibles) : null };
    });
    await page.screenshot({ path: `${CAPTURES}rapports-${largeur}.png`, fullPage: true });
    verifier(!metriques.overflowH, `rapports@${largeur} : aucun débordement horizontal`);
    if (metriques.cibleMin !== null) {
      verifier(largeur > 768 || metriques.cibleMin >= 44, `rapports@${largeur} : cible tactile mini ${metriques.cibleMin}px ≥ 44px`);
    }
  }
}

// ============================================================================
// 2. Agent stock : catalogue seulement, jamais de FCFA
// ============================================================================
{
  const { page } = await nouvellePage(390, 844);
  await seConnecter(page, "magasin.stock", MDP_AGENT_STOCK);
  await page.goto(`${SERVEUR_URL}/app/stock.html`, { waitUntil: "networkidle" });
  await page.click("text=Rapports");
  await page.waitForURL(/rapports\.html/, { timeout: 10000 });
  await page.waitForLoadState("networkidle");

  verifier(await page.isVisible("#carte-export-articles"), "agent stock : export du catalogue visible");
  verifier(!(await page.isVisible("#carte-historique")), "agent stock : historique des comptages absent");
  verifier(!(await page.isVisible("#carte-export-ventes")), "agent stock : export des ventes absent");

  const texteDom = await page.evaluate(() => document.body.innerText);
  verifier(!/FCFA/i.test(texteDom), "agent stock : aucune occurrence de « FCFA » sur rapports.html");

  const entete = await telechargerEtLireEntete(page, "#export-articles-xlsx");
  verifier(entete.startsWith("PK"), "agent stock : export du catalogue réellement téléchargé");
}

// ============================================================================
// 3. Agent comptabilité : catalogue + ventes, jamais l'historique
// ============================================================================
{
  const { page } = await nouvellePage();
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);
  await page.goto(`${SERVEUR_URL}/app/vente.html`, { waitUntil: "networkidle" });
  await page.click("text=Rapports");
  await page.waitForURL(/rapports\.html/, { timeout: 10000 });
  await page.waitForLoadState("networkidle");

  verifier(await page.isVisible("#carte-export-articles"), "agent comptabilité : export du catalogue visible");
  verifier(await page.isVisible("#carte-export-ventes"), "agent comptabilité : export des ventes visible");
  verifier(!(await page.isVisible("#carte-historique")), "agent comptabilité : historique des comptages absent");

  const entete = await telechargerEtLireEntete(page, "#export-ventes-pdf");
  verifier(entete.startsWith("%PDF"), "agent comptabilité : export des ventes .pdf réellement téléchargé");
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
