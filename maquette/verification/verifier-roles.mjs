/* Matrice des rôles PAR EXÉCUTION RÉELLE (chantier C8, cycle 65) :

   1. Captures d'écran par rôle : écran d'accueil, pages autorisées, et
      preuve visuelle du REFUS d'une page interdite (l'UI redirige vers
      l'accueil du rôle — jamais une erreur nue).
   2. Changement de mot de passe PROVISOIRE forcé (correctif du cycle 65) :
      un compte au drapeau TRUE est renvoyé vers changer-mot-de-passe.html
      à la connexion, un deep-link vers une autre page est ramené au même
      écran, le serveur refuse le reste (403, prouvé en pytest), et le
      changement réussi libère la session.
   3. Cumul de rôles : un compte portant agent_stock + agent_comptabilite
      est accepté par l'API sur les deux périmètres (test_cumul_roles.py),
      mais l'UI ne regarde que le rôle PRINCIPAL — divergence documentée
      dans RAPPORT_TESTS_ROLES.md, pas corrigée (décision d'ergonomie).

   Prérequis : serveur démarré sur SERVEUR_URL (défaut http://127.0.0.1:8010),
   servant /app. Réinitialise elle-même la base (jeu d'essai, mots de passe
   bcrypt réels, comptes temporaires tmp.force et tmp.cumul supprimés après).
*/
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { existsSync, mkdirSync } from "node:fs";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE_DEPOT = resolve(ICI, "..", "..");
const CAPTURES = resolve(ICI, "..", "captures", "roles") + "/";

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
const MDP_TMP_FORCE = "TmpForce123";
const MDP_TMP_CUMUL = "TmpCumul123";

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

console.log("== Préparation (base + comptes temporaires) ==");
execFileSync(PSQL, [
  "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
  "-v", "ON_ERROR_STOP=1", "-q", "-f", resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"),
], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
// Compte au mot de passe provisoire NON changé (drapeau imposé).
psql(`DELETE FROM utilisateurs_roles WHERE utilisateur_id IN (SELECT id FROM utilisateurs WHERE identifiant LIKE 'tmp.%');
      DELETE FROM utilisateurs WHERE identifiant LIKE 'tmp.%';
      INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash, role, site_id, doit_changer_mot_de_passe)
      VALUES ('Test Force', 'tmp.force', crypt('${MDP_TMP_FORCE}', gen_salt('bf', 12)), 'agent_comptabilite', 1, TRUE);
      INSERT INTO utilisateurs_roles (utilisateur_id, role)
      SELECT id, role FROM utilisateurs WHERE identifiant = 'tmp.force';`);
// Compte à rôles cumulés : principal agent_stock, second agent_comptabilite.
psql(`INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash, role, site_id, doit_changer_mot_de_passe)
      VALUES ('Test Cumul', 'tmp.cumul', crypt('${MDP_TMP_CUMUL}', gen_salt('bf', 12)), 'agent_stock', 1, FALSE);
      INSERT INTO utilisateurs_roles (utilisateur_id, role) VALUES
      ((SELECT id FROM utilisateurs WHERE identifiant='tmp.cumul'), 'agent_stock'),
      ((SELECT id FROM utilisateurs WHERE identifiant='tmp.cumul'), 'agent_comptabilite');`);

if (!existsSync(CAPTURES)) mkdirSync(CAPTURES, { recursive: true });
console.log("Prêt.\n");

const navigateur = await chromium.launch({ channel: "chrome" });

async function nouvellePage() {
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  return { contexte, page: await contexte.newPage() };
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
  return reponse.ok();
}

async function capturer(page, nom) {
  await page.screenshot({ path: CAPTURES + nom + ".png", fullPage: false });
}

// Pages contrôlées par rôle : autorisées (capture sur place) et refusées
// (l'UI doit rediriger vers l'accueil du rôle — capture de la page d'arrivée).
const ROLES = [
  {
    cle: "responsable", identifiant: "resp", mdp: MDP_RESPONSABLE,
    accueil: "tableau-bord.html",
    autorisees: ["comptes", "rh", "declarations", "cloture-caisse"],
    refusees: ["inventaire"],
  },
  {
    cle: "agent-comptabilite", identifiant: "magasin.compta", mdp: MDP_AGENT_COMPTA,
    accueil: "vente.html",
    autorisees: ["clients", "rapports"],
    refusees: ["comptes", "tableau-bord"],
  },
  {
    cle: "agent-stock", identifiant: "magasin.stock", mdp: MDP_AGENT_STOCK,
    accueil: "inventaire.html",
    autorisees: ["stock", "rapports"],
    refusees: ["vente", "clients"],
  },
];

for (const role of ROLES) {
  const { contexte, page } = await nouvellePage();

  if (role.cle === "responsable") {
    await page.goto(`${SERVEUR_URL}/app/connexion.html`, { waitUntil: "networkidle" });
    await capturer(page, "00-connexion");
  }

  const connecte = await seConnecter(page, role.identifiant, role.mdp);
  verifier(connecte, `${role.cle} : connexion`);
  verifier(page.url().endsWith("/app/" + role.accueil),
    `${role.cle} : accueil = ${role.accueil} (obtenu : ${page.url().split("/app/")[1] || page.url()})`);
  await capturer(page, `${role.cle}-01-accueil-${role.accueil.replace(".html", "")}`);

  let n = 2;
  for (const base of role.autorisees) {
    await page.goto(`${SERVEUR_URL}/app/${base}.html`, { waitUntil: "networkidle" });
    const surPlace = page.url().endsWith(`/app/${base}.html`);
    verifier(surPlace, `${role.cle} : page autorisée ${base}.html accessible`);
    await capturer(page, `${role.cle}-0${n}-${base}`);
    n += 1;
  }

  for (const base of role.refusees) {
    await page.goto(`${SERVEUR_URL}/app/${base}.html`, { waitUntil: "networkidle" });
    // exigerSession redirige vers l'accueil du rôle : on attend le changement.
    await page.waitForURL((u) => !u.pathname.endsWith(`/${base}.html`), { timeout: 10000 })
      .catch(() => {});
    await page.waitForLoadState("networkidle");
    const redirige = page.url().endsWith("/app/" + role.accueil);
    verifier(redirige,
      `${role.cle} : page refusée ${base}.html redirigée vers ${role.accueil} (obtenu : ${page.url().split("/app/")[1] || page.url()})`);
    await capturer(page, `${role.cle}-refuse-${base}`);
  }

  await contexte.close();
}

// ============================================================================
// Changement de mot de passe provisoire forcé (correctif cycle 65)
// ============================================================================
{
  const { contexte, page } = await nouvellePage();
  const connecte = await seConnecter(page, "tmp.force", MDP_TMP_FORCE);
  verifier(connecte, "force : connexion avec mot de passe provisoire");
  verifier(page.url().endsWith("/app/changer-mot-de-passe.html"),
    `force : renvoyé vers changer-mot-de-passe.html (obtenu : ${page.url().split("/app/")[1] || page.url()})`);
  await capturer(page, "force-01-ecran-changement-impose");

  // Deep-link : ouvrir une page métier directement ramenée à l'écran de
  // changement (garde exigerSession, cycle 65).
  await page.goto(`${SERVEUR_URL}/app/vente.html`, { waitUntil: "networkidle" });
  await page.waitForURL((u) => u.pathname.endsWith("/changer-mot-de-passe.html"), { timeout: 10000 })
    .catch(() => {});
  verifier(page.url().endsWith("/app/changer-mot-de-passe.html"),
    "force : deep-link vers vente.html ramené à l'écran de changement");
  await capturer(page, "force-02-deep-link-bloque");

  // Mauvais mot de passe actuel : message serveur affiché, on reste bloqué.
  await page.fill("#actuel", "mauvais-mot-de-passe");
  await page.fill("#nouveau", "TmpNouveau456");
  await page.fill("#confirmation", "TmpNouveau456");
  await page.click("#bouton-valider");
  await page.waitForSelector("#zone-erreur:not([hidden])", { timeout: 10000 });
  const messageErreur = await page.textContent("#zone-erreur");
  verifier(messageErreur.includes("Mot de passe actuel incorrect"),
    `force : mauvais actuel refusé avec le message serveur (obtenu : ${messageErreur})`);
  await capturer(page, "force-03-mauvais-actuel-refuse");

  // Changement réussi : redirection vers l'accueil du rôle, drapeau local faux.
  await page.fill("#actuel", MDP_TMP_FORCE);
  await page.click("#bouton-valider");
  await page.waitForURL((u) => u.pathname.endsWith("/vente.html"), { timeout: 10000 })
    .catch(() => {});
  verifier(page.url().endsWith("/app/vente.html"),
    `force : changement réussi -> accueil comptabilité (obtenu : ${page.url().split("/app/")[1] || page.url()})`);
  const drapeau = await page.evaluate(() => JSON.parse(sessionStorage.getItem("qf_session")).doit_changer_mot_de_passe);
  verifier(drapeau === false, "force : drapeau local repassé à faux après changement");
  await capturer(page, "force-04-session-liberee");
  await contexte.close();
}

// ============================================================================
// Cumul de rôles : l'API accepte les deux périmètres, l'UI ne regarde que le
// rôle principal (divergence documentée, non corrigée)
// ============================================================================
{
  const { contexte, page } = await nouvellePage();
  const connecte = await seConnecter(page, "tmp.cumul", MDP_TMP_CUMUL);
  verifier(connecte, "cumul : connexion");
  verifier(page.url().endsWith("/app/inventaire.html"),
    `cumul : accueil = inventaire.html (rôle principal agent_stock) (obtenu : ${page.url().split("/app/")[1] || page.url()})`);

  // L'API accepte ce compte sur le périmètre comptabilité (rôle secondaire) :
  // preuve directe par appel réel, puisque l'UI ne le laissera pas passer.
  const apiAccepte = await page.evaluate(async () => {
    const session = JSON.parse(sessionStorage.getItem("qf_session"));
    const reponse = await fetch("/ventes/parametres", {
      headers: { Authorization: "Bearer " + session.jeton },
    });
    return reponse.status;
  });
  verifier(apiAccepte === 200, `cumul : l'API accepte GET /ventes/parametres (rôle secondaire) -> ${apiAccepte}`);

  // ... mais l'écran vente.html redirige (exigerSession ne regarde que le
  // rôle principal de /moi).
  await page.goto(`${SERVEUR_URL}/app/vente.html`, { waitUntil: "networkidle" });
  await page.waitForURL((u) => !u.pathname.endsWith("/vente.html"), { timeout: 10000 }).catch(() => {});
  verifier(page.url().endsWith("/app/inventaire.html"),
    `cumul : vente.html refusée par l'UI (rôle principal seul) -> ${page.url().split("/app/")[1] || page.url()}`);
  await capturer(page, "cumul-01-ui-refuse-perimetre-secondaire");

  await contexte.close();
}

// Nettoyage : les journaux (journal_connexions, journal_comptes) refusent
// tout DELETE ligne à ligne depuis la migration 004 — c'est voulu, l'audit ne
// se supprime pas. Le mécanisme prévu par le dépôt pour une remise à zéro de
// test est le TRUNCATE du jeu d'essai (00_jeu_essai.sql, qui ne déclenche pas
// ces déclencheurs) : on le recharge tel quel, il emporte les comptes tmp.%
// en CASCADE. On ré-applique ensuite les mots de passe bcrypt réels pour
// laisser la base dans l'état canonique attendu par les autres suites.
console.log("\n== Nettoyage (rejeu d'essai — les comptes tmp.% partent en CASCADE) ==");
execFileSync(PSQL, [
  "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
  "-v", "ON_ERROR_STOP=1", "-q", "-f", resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"),
], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
psql(`UPDATE utilisateurs SET mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);
psql(`UPDATE utilisateurs SET mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
const resteTmp = psqlValeur(`SELECT count(*) FROM utilisateurs WHERE identifiant LIKE 'tmp.%';`);
verifier(resteTmp === "0", `nettoyage : aucun compte tmp.% résiduel (restant : ${resteTmp})`);

console.log(`\nOK : ${ok.length}`);
for (const l of ok) console.log("  ✓ " + l);
if (ko.length) {
  console.log(`KO : ${ko.length}`);
  for (const l of ko) console.log("  ✗ " + l);
}

await navigateur.close();

if (ko.length) process.exit(1);
console.log("\nTous les contrôles de la matrice des rôles sont passés.");
