/* Vérifie, PAR EXÉCUTION RÉELLE, que l'écran Comptes (cycle 32, chantier C2)
   câble réellement les routes /admin/comptes (server/app/routes/comptes.py,
   CDC §3.8, décision du 2026-09-20) :

   1. Le responsable accède à comptes.html ; l'agent stock et l'agent
      comptabilité sont redirigés (accès refusé).
   2. Un compte créé depuis l'écran est réellement enregistré (POST
      /admin/comptes) et réapparaît dans la liste.
   3. La désactivation depuis l'écran est réelle : la pastille change, la
      connexion de ce compte est refusée (« désactivé »), puis la
      réactivation rend la connexion de nouveau possible.
   4. Aucun hachage de mot de passe n'apparaît dans la page.
   5. Mise en page aux 5 largeurs habituelles, captures incluses.

   Prérequis : serveur démarré sur SERVEUR_URL, servant /app.
   Réinitialise elle-même la base (jeu d'essai + mots de passe réels).
*/
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { existsSync } from "node:fs";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE_DEPOT = resolve(ICI, "..", "..");

const SERVEUR_URL = process.env.SERVEUR_URL || "http://127.0.0.1:8010";
const DB_PISTE = process.env.PGDATABASE_PISTE || "quincaillerie_test";
let PGDEV = resolve(RACINE_DEPOT, "_pgdev");
if (!existsSync(PGDEV)) {
  PGDEV = resolve(RACINE_DEPOT, "..", "..", "_pgdev");
}
const PSQL = resolve(PGDEV, "pgsql", "bin", "psql.exe");

const MDP_RESPONSABLE = "ResponsableTest123";
const MDP_AGENT_STOCK = "AgentStockTest123";
const MDP_AGENT_COMPTA = "AgentComptaTest123";
const NOUVEAU_IDENTIFIANT = "c2.agent";
const NOUVEAU_MDP = "C2AgentTest123";
const NOUVEAU_MDP_RESET = "C2AgentReset123";

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
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
psql(`DELETE FROM utilisateurs WHERE identifiant = '${NOUVEAU_IDENTIFIANT}';`);
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
  await page.screenshot({ path: `${CAPTURES}comptes-${largeur}.png`, fullPage: true });
  verifier(!metriques.overflowH, `comptes@${largeur} : aucun débordement horizontal`);
  if (metriques.cibleMin !== null) {
    verifier(largeur > 768 || metriques.cibleMin >= 44, `comptes@${largeur} : cible tactile mini ${metriques.cibleMin}px ≥ 44px`);
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
    await page.goto(`${SERVEUR_URL}/app/comptes.html`, { waitUntil: "networkidle" });
    verifier(!page.url().endsWith("comptes.html"), `${identifiant} : accès direct à comptes.html -> redirigé`);
    await contexte.close();
  }
}

// ============================================================================
// 2. Mise en page aux 5 largeurs, responsable connecté
// ============================================================================
for (const largeur of [360, 390, 768, 1366, 1920]) {
  const contexte = await navigateur.newContext({
    viewport: { width: largeur, height: largeur < 700 ? 780 : largeur < 1400 ? 800 : 960 },
  });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/comptes.html`, { waitUntil: "networkidle" });
  await mesurerMiseEnPage(page, "comptes", largeur);
  await contexte.close();
}

// ============================================================================
// 3. Création depuis l'écran, désactivation, coupure de session, réactivation
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/comptes.html`, { waitUntil: "networkidle" });

  // Aucun hachage visible avant même la création.
  verifier(!(await page.content()).includes("$2a$"), "aucun hachage de mot de passe dans la page");

  await page.click("#bouton-formulaire");
  await page.fill("#compte-nom", "Agent C2");
  await page.fill("#compte-identifiant", NOUVEAU_IDENTIFIANT);
  await page.selectOption("#compte-role", "agent_comptabilite");
  await page.selectOption("#compte-site", "1");
  await page.fill("#compte-mot-de-passe", NOUVEAU_MDP);
  const [reponseCreation, reponseListe] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/admin/comptes") && r.request().method() === "POST", { timeout: 10000 }),
    page.waitForResponse((r) => r.url().endsWith("/admin/comptes") && r.request().method() === "GET", { timeout: 10000 }),
    page.click("#compte-valider"),
  ]);
  verifier(reponseCreation.ok(), "POST /admin/comptes réussi depuis l'écran");
  verifier(reponseListe.ok(), "la liste se recharge après la création");
  verifier(
    (await page.locator("li", { hasText: NOUVEAU_IDENTIFIANT }).count()) > 0,
    "le nouveau compte apparaît dans la liste"
  );

  // Désactivation depuis l'écran.
  const ligne = page.locator("li", { hasText: NOUVEAU_IDENTIFIANT });
  const [reponseDesactivation] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/actif") && r.request().method() === "PATCH", { timeout: 10000 }),
    ligne.getByRole("button", { name: "Désactiver" }).click(),
  ]);
  verifier(reponseDesactivation.ok(), "PATCH /admin/comptes/{id}/actif (désactivation) réussi");
  await page.waitForLoadState("networkidle");
  verifier((await ligne.textContent()).includes("Désactivé"), "la pastille passe à « Désactivé »");

  // La connexion du compte désactivé est refusée.
  {
    const contexteAgent = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
    const pageAgent = await contexteAgent.newPage();
    await seConnecter(pageAgent, NOUVEAU_IDENTIFIANT, NOUVEAU_MDP);
    await pageAgent.waitForSelector("#zone-erreur:not([hidden])", { timeout: 10000 });
    const message = await pageAgent.textContent("#zone-erreur");
    verifier(message.includes("désactivé"), "connexion refusée pour un compte désactivé (« désactivé » affiché)");
    await contexteAgent.close();
  }

  // Réactivation depuis l'écran.
  const [reponseReactivation] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/actif") && r.request().method() === "PATCH", { timeout: 10000 }),
    page.locator("li", { hasText: NOUVEAU_IDENTIFIANT }).getByRole("button", { name: "Réactiver" }).click(),
  ]);
  verifier(reponseReactivation.ok(), "PATCH /admin/comptes/{id}/actif (réactivation) réussi");

  // La connexion fonctionne de nouveau.
  {
    const contexteAgent = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
    const pageAgent = await contexteAgent.newPage();
    await seConnecter(pageAgent, NOUVEAU_IDENTIFIANT, NOUVEAU_MDP);
    verifier(!pageAgent.url().endsWith("connexion.html"), "connexion de nouveau possible après réactivation");
    await contexteAgent.close();
  }

  // Réinitialisation du mot de passe depuis l'écran (cycle 38) : le
  // responsable saisit le nouveau mot de passe dans la boîte de dialogue,
  // l'ancien est refusé, le nouveau est accepté avec changement forcé.
  page.once("dialog", (dialogue) => dialogue.accept(NOUVEAU_MDP_RESET));
  const [reponseReset] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/mot-de-passe") && r.request().method() === "PATCH", { timeout: 10000 }),
    page.locator("li", { hasText: NOUVEAU_IDENTIFIANT }).getByRole("button", { name: "Réinitialiser le mot de passe" }).click(),
  ]);
  verifier(reponseReset.ok(), "PATCH /admin/comptes/{id}/mot-de-passe (réinitialisation) réussi");

  {
    const contexteAgent = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
    const pageAgent = await contexteAgent.newPage();
    await seConnecter(pageAgent, NOUVEAU_IDENTIFIANT, NOUVEAU_MDP);
    await pageAgent.waitForSelector("#zone-erreur:not([hidden])", { timeout: 10000 });
    verifier(true, "l'ancien mot de passe est refusé après réinitialisation");
    await contexteAgent.close();
  }
  {
    const contexteAgent = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
    const pageAgent = await contexteAgent.newPage();
    await seConnecter(pageAgent, NOUVEAU_IDENTIFIANT, NOUVEAU_MDP_RESET);
    verifier(!pageAgent.url().endsWith("connexion.html"), "le nouveau mot de passe permet de se connecter");
    await contexteAgent.close();
  }

  await contexte.close();
}

console.log(`\n== ${ok.length}/${ok.length + ko.length} contrôles réussis ==`);
for (const libelle of ok) console.log(`  OK  ${libelle}`);
for (const libelle of ko) console.log(`  KO  ${libelle}`);
if (ko.length) process.exit(1);
