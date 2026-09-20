/* Vérifie, PAR EXÉCUTION RÉELLE, le correctif d'échappement HTML du cycle
   de correction après le cycle 7 : un nom d'article contenant une charge
   HTML/JS ne doit JAMAIS s'exécuter dans le navigateur, sur AUCUN écran qui
   l'affiche — ni dans les suggestions de recherche et le panier
   (vente.html), ni dans les écarts affichés au responsable
   (tableau-bord.html).

   Avant le correctif, les deux écrans construisaient ces listes avec
   `innerHTML` et une simple concaténation de chaînes.

   Prérequis : serveur démarré sur SERVEUR_URL, servant /app (cycle 5).
   Réinitialise elle-même la base (jeu d'essai + mots de passe réels), et y
   insère un article dont le nom porte la charge d'essai.
*/
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { writeFileSync, mkdtempSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";
import { tmpdir } from "node:os";

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

// Charge d'essai : si jamais interprétée comme HTML plutôt qu'affichée
// comme texte, l'attribut onerror pose un marqueur global détectable.
const NOM_MALVEILLANT = '<img src=x onerror="window.__xss_declenche = true">';

const ok = [], ko = [];
const verifier = (cond, libelle) => (cond ? ok : ko).push(libelle);

const DOSSIER_TEMP = mkdtempSync(join(tmpdir(), "qf-echappement-"));

// Écrit dans un fichier temporaire (-f) plutôt que de passer par -c : un
// argument de ligne de commande avec des caractères accentués (« pièce »)
// se corrompt silencieusement sous Windows selon l'encodage du process
// enfant, alors qu'un fichier lu explicitement en UTF-8 par psql ne pose
// aucun problème (même mécanisme que db/tests/00_jeu_essai.sql).
function psql(sql) {
  const fichier = join(DOSSIER_TEMP, `essai-${Date.now()}-${Math.random().toString(36).slice(2)}.sql`);
  writeFileSync(fichier, sql, { encoding: "utf8" });
  execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
    "-v", "ON_ERROR_STOP=1", "-q", "-f", fichier,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
}

console.log("== Préparation de la base (jeu d'essai + article malveillant) ==");
execFileSync(PSQL, [
  "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
  "-v", "ON_ERROR_STOP=1", "-q", "-f", resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"),
], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);
// Article du site 1, stock 1 : une vente de 3 dessus produit un écart
// affiché au tableau de bord, avec ce nom malveillant.
psql(`INSERT INTO articles (nom, categorie, unite, prix_achat, prix_vente, quantite_stock, seuil_alerte, site_id, fournisseur_id)
       VALUES ('${NOM_MALVEILLANT.replace(/'/g, "''")}', 'Essai', 'pièce', 1000, 2000, 1, 1, 1, 1);`);
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

async function xssDeclenche(page) {
  return page.evaluate(() => window.__xss_declenche === true);
}

// ============================================================================
// 1. vente.html : suggestions de recherche + panier
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);
  verifier(page.url().endsWith("vente.html"), "comptable : connexion -> vente.html");

  await page.fill("#recherche", "img src");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  verifier(!(await xssDeclenche(page)), "vente : suggestions affichées, onerror NON déclenché");
  const texteSuggestions = await page.textContent("#suggestions");
  verifier(texteSuggestions.includes("<img"), "vente : le nom malveillant apparaît comme TEXTE dans les suggestions");

  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.getElementById("panier").children.length > 0, { timeout: 5000 });
  verifier(!(await xssDeclenche(page)), "vente : article ajouté au panier, onerror NON déclenché");
  const texteNomPanier = await page.textContent(".panier__nom");
  verifier(texteNomPanier.includes("<img"), "vente : le nom malveillant apparaît comme TEXTE dans le panier");
  const ariaLabel = await page.getAttribute(".panier__sup", "aria-label");
  verifier(ariaLabel.startsWith("Retirer <img"), `vente : l'attribut aria-label contient le nom tel quel, sans casser le HTML ("${ariaLabel}")`);

  await contexte.close();
}

// ============================================================================
// 2. tableau-bord.html : écarts d'inventaire ET écarts de vente
// ============================================================================
{
  // Comptage produisant un écart sur l'article malveillant (agent stock).
  const contexteAgent = await navigateur.newContext({ viewport: { width: 390, height: 844 } });
  const pageAgent = await contexteAgent.newPage();
  await seConnecter(pageAgent, "magasin.stock", MDP_AGENT_STOCK);
  await pageAgent.waitForFunction(() => !document.getElementById("bloc-comptage").hidden, { timeout: 10000 });
  // Compte tout ce qui se présente à 0 pour obtenir un écart sur chacun, y
  // compris l'article malveillant (peu importe l'ordre exact de la liste).
  let tours = 0;
  while (tours < 10) {
    const termine = await pageAgent.isVisible("#zone-fin:not([hidden])");
    if (termine) break;
    await pageAgent.fill("#saisie", "0");
    // Cycle 29 : un `waitForTimeout` fixe ici masquait la même bombe à
    // retardement que celle trouvée et corrigée dans
    // verifier-inventaire-reel.mjs (POST /inventaire/comptages non attendu
    // avant de boucler) — on attend la réponse réelle plutôt qu'un délai.
    await Promise.all([
      pageAgent.waitForResponse((r) => r.url().endsWith("/inventaire/comptages") && r.request().method() === "POST", { timeout: 10000 }),
      pageAgent.click("#btn-suivant"),
    ]);
    tours++;
  }
  await contexteAgent.close();

  // Vente à découvert sur l'article malveillant (stock 1, on en vend 3).
  const contexteCompta = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const pageCompta = await contexteCompta.newPage();
  await seConnecter(pageCompta, "magasin.compta", MDP_AGENT_COMPTA);
  await pageCompta.fill("#recherche", "img src");
  await pageCompta.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await pageCompta.keyboard.press("Enter");
  await pageCompta.waitForFunction(() => document.getElementById("panier").children.length > 0, { timeout: 5000 });
  await pageCompta.fill(".panier__ligne input.panier__mini", "3");
  await pageCompta.locator(".panier__ligne input.panier__mini").first().dispatchEvent("input");
  // N° facturier obligatoire (addendum point c, cycle 27) — le vendeur est
  // déjà présélectionné.
  await pageCompta.fill("#numero-facturier", "MAG-ECHAP01");
  await pageCompta.keyboard.press("F9");
  await pageCompta.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  await Promise.all([
    pageCompta.waitForResponse((r) => r.url().endsWith("/ventes") && r.request().method() === "POST", { timeout: 10000 }),
    pageCompta.keyboard.press("F9"),
  ]);
  await contexteCompta.close();

  // Tableau de bord du responsable : les deux listes affichent l'article.
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  verifier(page.url().endsWith("tableau-bord.html"), "responsable : connexion -> tableau-bord.html");

  await page.waitForFunction(
    () => !document.getElementById("liste-ecarts").textContent.includes("—") &&
          !document.getElementById("liste-ecarts-ventes").textContent.includes("—"),
    { timeout: 10000 }
  );
  verifier(!(await xssDeclenche(page)), "tableau de bord : chargé, onerror NON déclenché");

  const texteEcarts = await page.textContent("#liste-ecarts");
  verifier(texteEcarts.includes("<img"), "tableau de bord : nom malveillant en TEXTE dans « Écarts d'inventaire »");

  const texteEcartsVentes = await page.textContent("#liste-ecarts-ventes");
  verifier(texteEcartsVentes.includes("<img"), "tableau de bord : nom malveillant en TEXTE dans « Écarts de stock (ventes) »");

  // Vérification la plus stricte : aucun <img> réel n'a été créé dans le DOM
  // à partir de ce nom (seul du texte, jamais un élément).
  const nbBalisesImgReelles = await page.evaluate(() =>
    document.querySelectorAll("#liste-ecarts img, #liste-ecarts-ventes img").length
  );
  verifier(nbBalisesImgReelles === 0, `tableau de bord : aucune balise <img> réelle créée dans le DOM (trouvé : ${nbBalisesImgReelles})`);

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
