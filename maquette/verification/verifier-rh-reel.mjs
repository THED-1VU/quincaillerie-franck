/* Vérifie, PAR EXÉCUTION RÉELLE, que l'écran RH (cycle 18, chantier C6)
   câble réellement les routes de server/app/routes/rh.py (cycle 16, jamais
   exposées à un écran avant ce cycle) :

   1. Le responsable accède à rh.html, jamais l'agent stock ni l'agent
      comptabilité (CDC §3.5).
   2. Un employé créé depuis l'écran est réellement enregistré (POST
      /rh/employes) et réapparaît dans la liste.
   3. Une absence/congé créée depuis l'écran est réellement enregistrée
      (POST /rh/absences-conges) et réapparaît, rattachée au bon employé.
   4. Une avance sur salaire créée depuis l'écran, puis remboursée par le
      bouton dédié, change réellement d'état côté serveur (POST
      /rh/avances-salaire puis POST /rh/avances-salaire/{id}/rembourser).

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
// (jamais quincaillerie_test) sans modifier ce fichier commun aux trois —
// valeurs par défaut inchangées pour le dépôt principal.
const PGDEV = resolve(process.env.PGDEV_RACINE || RACINE_DEPOT, "_pgdev");
const PSQL = resolve(PGDEV, "pgsql", "bin", "psql.exe");
const BASE = process.env.PGDATABASE_PISTE || "quincaillerie_test";

const MDP_RESPONSABLE = "ResponsableTest123";
const MDP_AGENT_STOCK = "AgentStockTest123";
const MDP_AGENT_COMPTA = "AgentComptaTest123";

const ok = [], ko = [];
const verifier = (cond, libelle) => (cond ? ok : ko).push(libelle);

function psql(sql) {
  execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", BASE, "-q", "-c", sql,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
}

console.log("== Préparation de la base (jeu d'essai + comptes de test) ==");
execFileSync(PSQL, [
  "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", BASE,
  "-v", "ON_ERROR_STOP=1", "-q", "-f", resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"),
], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
console.log("Base prête.\n");

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
  await page.screenshot({ path: `${CAPTURES}rh-${largeur}.png`, fullPage: true });
  verifier(!metriques.overflowH, `rh@${largeur} : aucun débordement horizontal`);
  if (metriques.cibleMin !== null) {
    verifier(largeur > 768 || metriques.cibleMin >= 44, `rh@${largeur} : cible tactile mini ${metriques.cibleMin}px ≥ 44px`);
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
    await page.goto(`${SERVEUR_URL}/app/rh.html`, { waitUntil: "networkidle" });
    verifier(!page.url().endsWith("rh.html"), `${identifiant} : accès direct à rh.html -> reredirigé`);
    await contexte.close();
  }
}

// ============================================================================
// 2. Mise en page aux 5 largeurs habituelles, avec un responsable connecté
// ============================================================================
for (const largeur of [360, 390, 768, 1366, 1920]) {
  const contexte = await navigateur.newContext({
    viewport: { width: largeur, height: largeur < 700 ? 780 : largeur < 1400 ? 800 : 960 },
  });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/rh.html`, { waitUntil: "networkidle" });
  await mesurerMiseEnPage(page, "rh", largeur);
  await contexte.close();
}

// ============================================================================
// 3. Responsable : employé réel, absence/congé réelle, avance réelle + remboursement
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/rh.html`, { waitUntil: "networkidle" });
  verifier(page.url().endsWith("rh.html"), "responsable : accès à rh.html");

  const nomEmploye = "Test RH " + Date.now();

  await page.click("#bouton-nouvel-employe");
  await page.fill("#f-nom", nomEmploye);
  await page.fill("#f-poste", "Vendeur");
  await page.fill("#f-salaire", "75000");
  const [reponseEmploye] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/rh/employes") && r.request().method() === "POST", { timeout: 10000 }),
    page.locator("#carte-panneau button.btn--primaire").click(),
  ]);
  verifier(reponseEmploye.ok(), "employé réel : POST /rh/employes -> 201");
  const corpsEmploye = await reponseEmploye.json();

  await page.waitForFunction(
    (nom) => document.getElementById("liste-employes").textContent.includes(nom),
    nomEmploye, { timeout: 10000 }
  );
  verifier(true, "employé réel : réapparaît dans la liste après création");

  // --- Absence / congé, rattachée au nouvel employé ---
  await page.click("#bouton-nouvelle-absence");
  await page.selectOption("#panneau-contenu select", String(corpsEmploye.employe_id));
  const champsDate = await page.locator('#panneau-contenu input[type="date"]').all();
  await champsDate[0].fill("2026-10-01");
  await champsDate[1].fill("2026-10-05");
  const [reponseAbsence] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/rh/absences-conges") && r.request().method() === "POST", { timeout: 10000 }),
    page.locator("#carte-panneau button.btn--primaire").click(),
  ]);
  verifier(reponseAbsence.ok(), "absence/congé réelle : POST /rh/absences-conges -> 201");
  await page.waitForFunction(
    (nom) => document.getElementById("liste-absences").textContent.includes(nom),
    nomEmploye, { timeout: 10000 }
  );
  verifier(true, "absence/congé réelle : réapparaît dans la liste, rattachée au bon employé");

  // --- Avance sur salaire + remboursement ---
  await page.click("#bouton-nouvelle-avance");
  await page.selectOption("#panneau-contenu select", String(corpsEmploye.employe_id));
  await page.fill("#f-montant", "10000");
  const [reponseAvance] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/rh/avances-salaire") && r.request().method() === "POST", { timeout: 10000 }),
    page.locator("#carte-panneau button.btn--primaire").click(),
  ]);
  verifier(reponseAvance.ok(), "avance réelle : POST /rh/avances-salaire -> 201");
  await page.waitForFunction(
    (nom) => document.getElementById("liste-avances").textContent.includes(nom),
    nomEmploye, { timeout: 10000 }
  );
  verifier(true, "avance réelle : réapparaît dans la liste, non remboursée");

  const [reponseRemboursement] = await Promise.all([
    page.waitForResponse((r) => /\/rh\/avances-salaire\/\d+\/rembourser$/.test(r.url()) && r.request().method() === "POST", { timeout: 10000 }),
    page.locator("#liste-avances button:has-text('Rembourser')").first().click(),
  ]);
  verifier(reponseRemboursement.ok(), "remboursement réel : POST /rh/avances-salaire/{id}/rembourser -> 204");
  await page.waitForFunction(() => !document.querySelector("#liste-avances button"), { timeout: 10000 });
  verifier(true, "remboursement réel : plus aucun bouton « Rembourser » après remboursement");

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
