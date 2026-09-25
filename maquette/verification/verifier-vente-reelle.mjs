/* Vérifie, PAR EXÉCUTION RÉELLE, que l'écran de vente (cycle 6, chantier C5)
   enregistre désormais une VRAIE vente via POST /ventes, plus une SIMULATION :

   1. Le comptable ajoute un article réel au panier, valide (double F9), et
      voit un message de succès RÉEL (numéro de vente serveur, TVA calculée),
      plus AUCUNE occurrence du mot « SIMULATION ».
   2. Le crédit client n'est même pas proposable à l'écran (point b).
   3. Une vente à découvert de stock (article rare, stock 1) est quand même
      acceptée, avec un écart signalé à l'écran (point e).
   4. Le responsable, qui couvre deux sites, doit choisir un site avant de
      valider (le champ apparaît, la validation sans site est refusée).
   5. Le reçu PDF (cycle 19) apparaît après une vente réussie et se
      télécharge réellement (en-tête %PDF, jamais une simple vérification
      du code HTTP).

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

const MDP_AGENT_COMPTA = "AgentComptaTest123";
const MDP_RESPONSABLE = "ResponsableTest123";

const ok = [], ko = [];
const verifier = (cond, libelle) => (cond ? ok : ko).push(libelle);

// Même formule que fcfa() dans maquette/donnees-simulees.js, pour comparer
// un montant serveur au texte affiché à l'écran sans divergence d'arrondi
// d'affichage.
function fcfaAttendu(montant) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Math.round(montant)) + " FCFA";
}

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

// ============================================================================
// 1. Comptable : vente réelle, stock suffisant
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);
  verifier(page.url().endsWith("vente.html"), "comptable : connexion -> vente.html");

  // Le crédit client n'est même pas proposable.
  const optionsPaiement = await page.locator("#paiement option").allTextContents();
  verifier(!optionsPaiement.some((t) => /crédit/i.test(t)), "vente : crédit client absent des options de paiement");

  // Ajoute "Ciment CIM II 50 kg" (site 1, stock 30) au panier.
  await page.fill("#recherche", "ciment");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.getElementById("panier").textContent.includes("Ciment"), { timeout: 5000 });

  // L'APERÇU affiché AVANT confirmation doit correspondre exactement à ce
  // que le serveur confirmera (les prix sont TTC : la TVA s'extrait, elle ne
  // s'ajoute pas par-dessus — sinon l'aperçu et la confirmation divergent).
  const apercuTotalTtc = await page.textContent("#total-ttc");
  const apercuMontantTva = await page.textContent("#montant-tva");

  // N° facturier + vendeur, réels et obligatoires (addendum point c, cycle
  // 27). Vendeur = une fiche employé depuis le chantier B (migration 040),
  // plus jamais présélectionné — choix manuel explicite ici.
  await page.fill("#numero-facturier", "MAG-REEL01");
  await page.selectOption("#vendeur", "1");

  await page.keyboard.press("F9");
  await page.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  const [reponseVente] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/ventes") && r.request().method() === "POST", { timeout: 10000 }),
    page.keyboard.press("F9"),
  ]);
  verifier(reponseVente.ok(), "vente réelle : POST /ventes -> 201");
  const corpsVente = await reponseVente.json();
  verifier(
    apercuTotalTtc === fcfaAttendu(corpsVente.total_ttc) && apercuMontantTva === fcfaAttendu(corpsVente.montant_tva),
    `aperçu avant validation = confirmation serveur (aperçu : ${apercuTotalTtc} / ${apercuMontantTva}, `
    + `serveur : ${fcfaAttendu(corpsVente.total_ttc)} / ${fcfaAttendu(corpsVente.montant_tva)})`
  );
  await page.waitForFunction(() => !document.getElementById("zone-succes").hidden, { timeout: 10000 });

  const messageSucces = await page.textContent("#zone-succes");
  verifier(/^Vente n°\d+ enregistrée/.test(messageSucces), `vente réelle : message avec numéro de vente ("${messageSucces}")`);
  verifier(!/SIMULATION/i.test(messageSucces), "vente réelle : plus aucune mention SIMULATION");

  // Reçu PDF (cycle 19) : le bouton apparaît après la vente et déclenche un
  // VRAI téléchargement de navigateur (telechargerFichier(), api.js).
  verifier(await page.isVisible("#btn-imprimer-recu"), "vente réelle : bouton « Imprimer le reçu » visible après la vente");
  const [telechargement] = await Promise.all([
    page.waitForEvent("download", { timeout: 10000 }),
    page.click("#btn-imprimer-recu"),
  ]);
  const enteteRecu = readFileSync(await telechargement.path()).subarray(0, 4).toString("latin1");
  verifier(enteteRecu === "%PDF", `reçu réel : PDF réellement téléchargé (en-tête « ${enteteRecu}» )`);

  await contexte.close();
}

// ============================================================================
// 2. Comptable : vente à découvert de stock -> acceptée, écart signalé
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);

  // "Article rare" (site 1, stock 1) : on tente d'en vendre 3.
  await page.fill("#recherche", "rare");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.getElementById("panier").textContent.includes("rare"), { timeout: 5000 });
  // Porte la quantité à 3 dans le champ de la ligne.
  await page.fill(".panier__ligne input.panier__mini", "3");
  await page.locator(".panier__ligne input.panier__mini").first().dispatchEvent("input");

  await page.fill("#numero-facturier", "MAG-REEL02");
  await page.selectOption("#vendeur", "1");

  await page.keyboard.press("F9");
  await page.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  const [reponseVente2] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/ventes") && r.request().method() === "POST", { timeout: 10000 }),
    page.keyboard.press("F9"),
  ]);
  verifier(reponseVente2.ok(), "vente à découvert : POST /ventes -> 201 (jamais un refus, point e)");
  await page.waitForFunction(() => !document.getElementById("zone-succes").hidden, { timeout: 10000 });
  const messageEcart = await page.textContent("#zone-succes");
  verifier(/Stock insuffisant/i.test(messageEcart), `vente à découvert : écart signalé à l'écran ("${messageEcart}")`);

  await contexte.close();
}

// ============================================================================
// 3. Responsable : doit choisir un site avant de valider
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);
  await page.goto(`${SERVEUR_URL}/app/vente.html`, { waitUntil: "networkidle" });

  verifier(await page.isVisible("#champ-site"), "responsable : sélecteur de site visible sur l'écran de vente");

  await page.fill("#recherche", "clou");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.getElementById("panier").textContent.includes("Clou"), { timeout: 5000 });

  await page.keyboard.press("F9");
  await page.keyboard.press("F9");
  await page.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  const messageSansSite = await page.textContent("#zone-confirmation");
  verifier(/site/i.test(messageSansSite), `responsable sans site choisi : refus explicite ("${messageSansSite}")`);

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
