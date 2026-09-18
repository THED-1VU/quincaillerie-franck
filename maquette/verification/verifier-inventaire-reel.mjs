/* Vérifie, PAR EXÉCUTION RÉELLE, le chantier C7 (cycle 7) : comptage
   d'inventaire à l'aveugle et écarts.

   1. La liste à compter (inventaire.html) ne contient AUCUNE quantité —
      confirmé sur la page ET dans les réponses réseau observées.
   2. Un comptage soumis ne fait JAMAIS réapparaître la quantité attendue,
      ni la page, ni le réseau, ni le code source — même après un comptage
      créant un écart réel.
   3. Un article déjà compté disparaît de la liste au rechargement.
   4. Le tableau de bord du responsable affiche l'écart RÉEL (calculé par
      le serveur, jamais par la page) et l'écart de vente à découvert
      (chantier C5), tous deux absents avant ce cycle.

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
console.log("Base prête.\n");

const navigateur = await chromium.launch({ channel: "chrome" });

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

const motifsInterdits = /quantite_attendue|quantité attendue|"attendu"|attendu\s*:/i;

// ============================================================================
// 1. Agent stock : liste à compter sans quantité, comptage réel avec écart
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 390, height: 844 } });
  const page = await contexte.newPage();

  // Toutes les réponses JSON observées, pour l'inspection anti-fuite.
  const reponsesVues = [];
  page.on("response", async (reponse) => {
    if (reponse.url().startsWith(SERVEUR_URL) && reponse.headers()["content-type"]?.includes("json")) {
      try { reponsesVues.push(await reponse.text()); } catch { /* déjà consommée */ }
    }
  });

  await seConnecter(page, "magasin.stock", MDP_AGENT_STOCK);
  verifier(page.url().endsWith("inventaire.html"), "agent stock : connexion -> inventaire.html");

  // Moment forcé explicitement à "matin", plutôt que de dépendre du choix
  // par défaut de la page (heure du jour) : un contrôle ne doit pas dépendre
  // de l'heure à laquelle il tourne (constat trouvé par exécution après le
  // correctif de fuseau horaire — "matin"/"soir" par défaut a changé de
  // valeur avec l'heure locale correcte, ce que ce script supposait figé).
  await page.waitForFunction(() => !document.getElementById("bloc-comptage").hidden, { timeout: 10000 });
  await page.click("#btn-matin");
  await page.waitForFunction(() => !document.getElementById("bloc-comptage").hidden, { timeout: 10000 });
  const nomAffiche = await page.textContent("#art-nom");
  verifier(!!nomAffiche && nomAffiche !== "—", "inventaire : un article réel est affiché");

  // "Ciment CIM II 50 kg" (id 1, stock réel 30) : on saisit 22 -> écart réel -8,
  // qui ne doit JAMAIS remonter jusqu'ici.
  let compteurGardeFou = 0;
  while ((await page.textContent("#art-nom")) !== "Ciment CIM II 50 kg" && compteurGardeFou < 20) {
    await page.click("#btn-passer");
    await page.waitForTimeout(50);
    compteurGardeFou++;
  }
  verifier(compteurGardeFou < 20, "inventaire : « Ciment CIM II 50 kg » atteint dans la liste");

  await page.fill("#saisie", "22");
  await page.click("#btn-suivant");
  await page.waitForTimeout(300); // laisse la requête POST + l'avancée locale se faire

  const contenuPage = await page.content();
  const source = await page.evaluate(() => document.documentElement.outerHTML);
  verifier(!motifsInterdits.test(contenuPage), "inventaire : aucune 'quantité attendue' dans le HTML rendu après un comptage réel");
  verifier(!motifsInterdits.test(source), "inventaire : aucune 'quantité attendue' dans le code source de la page");
  verifier(
    reponsesVues.every((corps) => !motifsInterdits.test(corps)),
    `inventaire : aucune 'quantité attendue' dans les ${reponsesVues.length} réponse(s) réseau observée(s)`
  );

  await contexte.close();
}

// ============================================================================
// 2. Un article déjà compté disparaît de la liste au rechargement
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 390, height: 844 } });
  const page = await contexte.newPage();
  await seConnecter(page, "magasin.stock", MDP_AGENT_STOCK);
  await page.waitForFunction(() => !document.getElementById("bloc-comptage").hidden, { timeout: 10000 });

  const listeAvant = await page.evaluate(async () => {
    const session = JSON.parse(sessionStorage.getItem("qf_session"));
    const r = await fetch("/inventaire/articles-a-compter?moment=matin", { headers: { Authorization: "Bearer " + session.jeton } });
    return (await r.json()).articles.map((a) => a.nom);
  });
  verifier(!listeAvant.includes("Ciment CIM II 50 kg"), "inventaire : l'article déjà compté (section 1) n'est plus dans la liste du matin");

  await contexte.close();
}

// ============================================================================
// 3. Tableau de bord du responsable : écarts réels (comptage + ventes)
// ============================================================================
{
  // Contexte dédié au comptable : génère un écart de vente à découvert
  // ("Article rare", id 4, stock réel 1, on en vend 3).
  const contexteCompta = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const pageCompta = await contexteCompta.newPage();
  await seConnecter(pageCompta, "magasin.compta", MDP_AGENT_COMPTA);
  await pageCompta.fill("#recherche", "rare");
  await pageCompta.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await pageCompta.keyboard.press("Enter");
  await pageCompta.waitForFunction(() => document.getElementById("panier").textContent.includes("rare"), { timeout: 5000 });
  await pageCompta.fill(".panier__ligne input.panier__mini", "3");
  await pageCompta.locator(".panier__ligne input.panier__mini").first().dispatchEvent("input");
  // N° facturier obligatoire (addendum point c, cycle 27) — le vendeur est
  // déjà présélectionné.
  await pageCompta.fill("#numero-facturier", "MAG-INV01");
  await pageCompta.keyboard.press("F9");
  await pageCompta.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  await Promise.all([
    pageCompta.waitForResponse((r) => r.url().endsWith("/ventes") && r.request().method() === "POST", { timeout: 10000 }),
    pageCompta.keyboard.press("F9"),
  ]);
  await contexteCompta.close();

  // Contexte séparé pour le responsable : une session déjà active dans le
  // même contexte ferait rediriger connexion.html avant même d'afficher le
  // formulaire (garde de connexion.html, cycle 5).
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  verifier(page.url().endsWith("tableau-bord.html"), "responsable : connexion -> tableau-bord.html");

  await page.waitForFunction(
    () => !document.getElementById("liste-ecarts").textContent.includes("—"),
    { timeout: 10000 }
  );
  const texteEcarts = await page.textContent("#liste-ecarts");
  verifier(texteEcarts.includes("Ciment CIM II 50 kg"), "tableau de bord : écart de comptage réel affiché (Ciment)");
  verifier(/écart\s*-8/.test(texteEcarts.replace(/\s+/g, " ")) || texteEcarts.includes("-8"), `tableau de bord : écart correctement calculé (-8), lu : "${texteEcarts}"`);

  const texteEcartsVentes = await page.textContent("#liste-ecarts-ventes");
  verifier(texteEcartsVentes.includes("Article rare"), "tableau de bord : écart de vente à découvert affiché (Article rare)");
  verifier(texteEcartsVentes.includes("manque 2"), `tableau de bord : quantité manquante correcte (2), lu : "${texteEcartsVentes}"`);

  await contexte.close();
}

// ============================================================================
// 4. Panne réseau simulée par une double soumission (409) : l'agent doit
//    pouvoir avancer normalement, pas rester bloqué sur une « erreur » qui
//    n'en est pas une (le comptage est en réalité déjà enregistré). Deux
//    onglets du même compte, chacun avec sa propre liste chargée AVANT que
//    l'autre ne soumette — exactement le cas d'une réponse jamais revenue
//    au premier essai, suivie d'une nouvelle tentative.
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 390, height: 844 } });
  const pageA = await contexte.newPage();
  const pageB = await contexte.newPage();
  await seConnecter(pageA, "magasin.stock", MDP_AGENT_STOCK);
  await seConnecter(pageB, "magasin.stock", MDP_AGENT_STOCK);
  await pageA.waitForFunction(() => !document.getElementById("bloc-comptage").hidden, { timeout: 10000 });
  await pageB.waitForFunction(() => !document.getElementById("bloc-comptage").hidden, { timeout: 10000 });
  // Moment forcé (mêmes raisons que la section 1) : les deux onglets sur
  // "matin" explicitement, pas sur le choix par défaut de l'heure du jour.
  await pageA.click("#btn-matin");
  await pageA.waitForFunction(() => !document.getElementById("bloc-comptage").hidden, { timeout: 10000 });
  await pageB.click("#btn-matin");
  await pageB.waitForFunction(() => !document.getElementById("bloc-comptage").hidden, { timeout: 10000 });

  async function allerA(page, nomCible) {
    let tours = 0;
    while ((await page.textContent("#art-nom")) !== nomCible && tours < 20) {
      await page.click("#btn-passer");
      await page.waitForTimeout(50);
      tours++;
    }
    return (await page.textContent("#art-nom")) === nomCible;
  }

  const cible = "Fer à béton 8 mm";
  verifier(await allerA(pageA, cible), `409 : onglet A atteint « ${cible} »`);
  verifier(await allerA(pageB, cible), `409 : onglet B atteint « ${cible} », sur sa PROPRE liste chargée avant la soumission de A`);

  // Onglet A compte réellement -> succès normal, la vraie soumission.
  await pageA.fill("#saisie", "40");
  await pageA.click("#btn-suivant");
  await pageA.waitForTimeout(300);

  // Onglet B ignore que A vient de le faire (de son point de vue, c'est
  // comme si SA PROPRE tentative précédente avait échoué sans réponse) et
  // tente la même soumission -> le serveur répond 409.
  await pageB.fill("#saisie", "40");
  const [reponseB] = await Promise.all([
    pageB.waitForResponse((r) => r.url().endsWith("/inventaire/comptages") && r.request().method() === "POST", { timeout: 10000 }),
    pageB.click("#btn-suivant"),
  ]);
  verifier(reponseB.status() === 409, `409 : le serveur refuse bien le second envoi (statut ${reponseB.status()})`);
  await pageB.waitForTimeout(300);

  verifier(await pageB.isHidden("#zone-erreur-saisie"), "409 : aucun message d'erreur bloquant affiché à l'agent (onglet B)");
  const encoreSurCible = (await pageB.isVisible("#bloc-comptage")) && (await pageB.textContent("#art-nom")) === cible;
  verifier(!encoreSurCible, "409 : l'onglet B a avancé après le conflit, pas resté bloqué sur l'article");

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
