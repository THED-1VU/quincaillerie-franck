/* Vérifie, PAR EXÉCUTION RÉELLE, l'écran rapports.html (cycle 12) :
   historique des comptages et exports Excel/PDF du chantier C8, réels et
   testés au niveau API depuis le cycle 10 (server/tests/test_rapports.py),
   mais sans aucune interface jusqu'à ce cycle.

   Cycle 58 : rapport « écarts de prix par vendeur » (migration 048, point c
   question 5, décidé 2026-09-18) — 10 % SOUS le prix catalogue, seuil de
   configuration, signalement sans blocage. Une vente réelle est semée ici
   (5 720 = 12 % signalée, 5 980 = 8 % non signalée).

   Cycle 68 (écarts C7-02/C7-03 du registre) : l'historique restitue la
   régularisation du comptage semé (traçabilité 032, jamais effacée) et un
   6e export dédié — les écarts de comptage valorisés au prix d'achat,
   responsable seulement.

   1. Le responsable voit les 6 sections (historique, export articles,
      export stock valorisé — cycle 67, écart C4-02 —, écarts de comptage —
      cycle 68, écart C7-03 —, export ventes, écarts de prix) ; l'historique
      affiche un comptage réellement fait aujourd'hui AVEC sa régularisation,
      et rien sur une période passée. Le rapport des écarts affiche la vente
      semée, signale la ligne à 12 %, laisse visible celle à 8 %, et le
      filtre de période l'écarte.
   2. L'agent stock ne voit QUE l'export du catalogue (jamais l'historique,
      ni l'export des ventes, ni les écarts) — aucune occurrence de FCFA.
   3. L'agent comptabilité voit l'export du catalogue, des ventes et les
      écarts de prix, jamais l'historique (réservé au responsable).
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

// « Aujourd'hui » en UTC : date EXPLICITE de la semence du comptage plus
// bas, alignée sur le fuseau fixe imposé au navigateur (timezoneId UTC) —
// sans cela, autour de minuit, la date du navigateur et celle de la base
// peuvent diverger et fausser deux contrôles sans aucun défaut produit
// (constat cycle 67, machine de développement multi-fuseaux).
const AUJOURDHUI_UTC = new Date().toISOString().slice(0, 10);

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
// un vrai écart, pas seulement une ligne « conforme ». La date est posée
// EXPLICITEMENT en UTC (= « aujourd'hui » du navigateur, fuseau imposé plus
// bas) pour ne pas dépendre du fuseau de la base.
psql(`INSERT INTO comptages_stock (article_id, site_id, utilisateur_id, date_comptage, moment, quantite_comptee) VALUES (1, 1, 2, '${AUJOURDHUI_UTC}', 'matin', 28);`);

// Régularisation de cet écart par le responsable (cycle 68, écart C7-02) :
// traçabilité pure (032) — l'historique doit la restituer, jamais l'effacer.
psql(`INSERT INTO regularisations_ecarts_comptage (comptage_id, type_resolution, motif, decide_par_id)
      SELECT id, 'erreur_de_comptage', NULL, 1 FROM comptages_stock
       WHERE article_id = 1 AND site_id = 1 AND moment = 'matin'
         AND date_comptage::date = '${AUJOURDHUI_UTC}'::date;`);

// Vente réelle avec remises (cycle 58) : deux lignes au catalogue 6 500
// (Ciment), 5 720 = 12 % sous le catalogue (au-delà du seuil de 10 % →
// signalée) et 5 980 = 8 % (visible, non signalée), plus la recette
// cohérente — le même chemin qu'une vente encaissée par POST /ventes.
psql(`INSERT INTO ventes (id, site_id, utilisateur_id, statut, mode_paiement,
        utilisateur_caisse_id, sous_total_ht, taux_tva, montant_tva, total_ttc,
        date_encaissement, numero_facturier, vendeur_id)
      VALUES (905, 1, 4, 'payee', 'especes', 1, 11700, 0, 0, 11700, NOW(), 'MAG-UI-ECART', 1);`);
psql(`INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id, prix_catalogue, remise_montant)
      VALUES (905, 1, 1, 5720, 1, 6500, 780);`);
psql(`INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id, prix_catalogue, remise_montant)
      VALUES (905, 1, 1, 5980, 1, 6500, 520);`);
psql(`INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
      VALUES (1, 4, 'recette', 11700, 'Vente 905', 905);`);

console.log("Base prête.\n");

const navigateur = await chromium.launch({ channel: "chrome" });

// Fuseau fixe pour le navigateur : la carte « Historique des comptages »
// compare « aujourd'hui » (toISOString côté page) à la date du comptage
// semé ci-dessus (AUJOURDHUI_UTC). Sans fuseau imposé, le navigateur hérite
// du fuseau système (constat cycle 67 : machine en UTC-4, base et Node en
// UTC — autour de minuit, les deux « aujourd'hui » divergent). timezoneId
// UTC + date explicite en UTC à la semence rendent la comparaison
// déterministe partout.
async function nouvellePage(largeur = 1366, hauteur = 900) {
  const contexte = await navigateur.newContext({ viewport: { width: largeur, height: hauteur }, acceptDownloads: true, timezoneId: "UTC" });
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
// 1. Responsable : les 5 sections, historique réel, exports réels, écarts
// ============================================================================
{
  const { page } = await nouvellePage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/rapports.html`, { waitUntil: "networkidle" });
  verifier(page.url().endsWith("rapports.html"), "responsable : accès à rapports.html");

  for (const id of ["carte-historique", "carte-export-articles", "carte-export-stock", "carte-export-ecarts-comptage", "carte-export-ventes", "carte-ecarts-prix"]) {
    verifier(await page.isVisible(`#${id}`), `responsable : section #${id} visible`);
  }

  // Historique : la période par défaut est aujourd'hui -> le comptage semé plus haut apparaît,
  // avec sa régularisation (cycle 68, écart C7-02).
  await page.waitForSelector("#liste-historique li", { timeout: 5000 });
  const texteHistorique = await page.textContent("#liste-historique");
  verifier(texteHistorique.includes("Ciment"), "responsable : historique affiche le comptage réel du jour");
  verifier(texteHistorique.includes("-2") || texteHistorique.includes("écart"), "responsable : écart réel affiché (-2)");
  verifier(texteHistorique.includes("régularisé") && texteHistorique.includes("erreur_de_comptage"),
    "responsable : historique — la régularisation de l'écart est affichée");

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

  // Export du stock valorisé (cycle 67, écart C4-02) : réservé au
  // responsable — un vrai téléchargement, fichier substantiel (plusieurs
  // Ko : lignes + feuille « totaux par site »), comme les autres exports.
  const enteteStockXlsx = await telechargerEtLireEntete(page, "#export-stock-xlsx");
  verifier(enteteStockXlsx.startsWith("PK"), "responsable : export stock .xlsx réellement téléchargé");
  const contenuStock = await telechargerEtLireEntete(page, "#export-stock-xlsx", 1 << 20);
  verifier(contenuStock.length > 500, `responsable : export stock .xlsx substantiel (${contenuStock.length} octets lus)`);

  const enteteStockPdf = await telechargerEtLireEntete(page, "#export-stock-pdf");
  verifier(enteteStockPdf.startsWith("%PDF"), "responsable : export stock .pdf réellement téléchargé");

  // Export des écarts de comptage (cycle 68, écart C7-03) : réservé au
  // responsable — période par défaut aujourd'hui -> le fichier porte l'écart
  // semé plus haut ; vrai téléchargement, fichier substantiel.
  const enteteEcartsCptXlsx = await telechargerEtLireEntete(page, "#export-ecarts-comptage-xlsx");
  verifier(enteteEcartsCptXlsx.startsWith("PK"), "responsable : export écarts de comptage .xlsx réellement téléchargé");
  const contenuEcartsCpt = await telechargerEtLireEntete(page, "#export-ecarts-comptage-xlsx", 1 << 20);
  verifier(contenuEcartsCpt.length > 400, `responsable : export écarts de comptage .xlsx substantiel (${contenuEcartsCpt.length} octets lus)`);

  const enteteEcartsCptPdf = await telechargerEtLireEntete(page, "#export-ecarts-comptage-pdf");
  verifier(enteteEcartsCptPdf.startsWith("%PDF"), "responsable : export écarts de comptage .pdf réellement téléchargé");

  // Écarts de prix par vendeur (cycle 58) : la vente semée plus haut doit
  // apparaître — 12 % SIGNALÉE, 8 % visible mais non signalée, seuil 10 %.
  await page.waitForFunction(
    () => document.getElementById("liste-ecarts").textContent.includes("Employé Essai"),
    { timeout: 5000 }
  );
  const texteEcarts = await page.textContent("#liste-ecarts");
  verifier(texteEcarts.includes("MAG-UI-ECART"), "responsable : écarts — la vente réelle apparaît dans le rapport");
  verifier(texteEcarts.includes("SIGNALÉE"), "responsable : écarts — ligne à 12 % signalée au-delà du seuil");
  verifier(texteEcarts.includes("10 %"), "responsable : écarts — seuil configuré affiché (10 %)");
  verifier(texteEcarts.includes("12 %") && texteEcarts.includes("8 %"),
    "responsable : écarts — les deux écarts (12 % et 8 %) sont affichés");
  verifier(/\bsous le catalogue\b/.test(texteEcarts), "responsable : écarts — sens de l'écart explicite (sous le catalogue)");

  // Filtre de période réellement branché : une période passée vide la liste.
  await page.fill("#ecarts-debut", "2000-01-01");
  await page.fill("#ecarts-fin", "2000-01-02");
  await page.click("#ecarts-chercher");
  await page.waitForFunction(
    () => document.getElementById("liste-ecarts").textContent.includes("Aucun écart"),
    { timeout: 5000 }
  );
  verifier(true, "responsable : écarts — période passée -> aucun écart affiché");

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
  verifier(!(await page.isVisible("#carte-export-stock")), "agent stock : export du stock valorisé absent");
  verifier(!(await page.isVisible("#carte-export-ecarts-comptage")), "agent stock : export des écarts de comptage absent");
  verifier(!(await page.isVisible("#carte-export-ventes")), "agent stock : export des ventes absent");
  verifier(!(await page.isVisible("#carte-ecarts-prix")), "agent stock : rapport des écarts de prix absent");

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
  verifier(!(await page.isVisible("#carte-export-stock")), "agent comptabilité : export du stock valorisé absent");
  verifier(!(await page.isVisible("#carte-export-ecarts-comptage")), "agent comptabilité : export des écarts de comptage absent");

  // Écarts de prix : accessibles à la comptabilité (même périmètre que
  // l'export des ventes), et la vente du site 1 est bien visible.
  verifier(await page.isVisible("#carte-ecarts-prix"), "agent comptabilité : rapport des écarts visible");
  await page.waitForFunction(
    () => document.getElementById("liste-ecarts").textContent.includes("MAG-UI-ECART"),
    { timeout: 5000 }
  );
  verifier(true, "agent comptabilité : écarts — la vente de son site apparaît");

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
