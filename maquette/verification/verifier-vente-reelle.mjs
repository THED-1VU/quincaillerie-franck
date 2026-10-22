/* Vérifie, PAR EXÉCUTION RÉELLE, que l'écran de vente (cycle 6, chantier C5)
   enregistre désormais une VRAIE vente via POST /ventes, plus une SIMULATION :

   1. Le comptable ajoute un article réel au panier, valide (double F9), et
      voit un message de succès RÉEL (numéro de vente serveur, TVA calculée),
      plus AUCUNE occurrence du mot « SIMULATION ».
   2. Le crédit client est PROPOSÉ à l'écran (point b fusionné) et son
      parcours complet est vérifié plus bas (section 4) : vente à crédit
      depuis l'écran, créance visible, règlement partiel, annulation refusée
      après règlement, annulation acceptée sur vente non réglée, retour
      marchandise sur vente à crédit (réduit la créance, aucune dépense).
   3. Une vente à découvert de stock (article rare, stock 1) est quand même
      acceptée, avec un écart signalé à l'écran (point e).
   4. Le responsable, qui couvre deux sites, doit choisir un site avant de
      valider (le champ apparaît, la validation sans site est refusée).
   5. Le reçu PDF (cycle 19) apparaît après une vente réussie et se
      télécharge réellement (en-tête %PDF, jamais une simple vérification
      du code HTTP).
   6. Remises (cycle 59) : écart au catalogue affiché par ligne après un
      prix négocié, remise globale saisie et répercutée sur l'aperçu, remise
      atteignant le total refusée AVANT tout envoi, puis vente réelle avec
      les deux remises contrôlée en base et dans la réponse serveur.

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
// `_pgdev` n'existe que sur le poste Windows ; en CI, `psql` est sur le PATH.
const PSQL = process.env.PSQL || (existsSync(resolve(PGDEV, "pgsql", "bin", "psql.exe")) ? resolve(PGDEV, "pgsql", "bin", "psql.exe") : "psql");

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

function psqlValeur(sql) {
  return execFileSync(PSQL, [
    "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE, "-tAc", sql,
  ], { env: { ...process.env, PGPASSWORD: "qf_dev_local" }, encoding: "utf8" }).trim();
}

console.log("== Préparation de la base (jeu d'essai + comptes de test) ==");
execFileSync(PSQL, [
  "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", DB_PISTE,
  "-v", "ON_ERROR_STOP=1", "-q", "-f", resolve(RACINE_DEPOT, "db", "tests", "00_jeu_essai.sql"),
], { env: { ...process.env, PGPASSWORD: "qf_dev_local" } });
// Idempotence entre passages : `clients` n'est PAS purgé par le jeu d'essai
// (aucune TRUNCATE ne l'atteint). Un client marqueur d'un passage précédent
// ferait échouer le suivant : le `LIMIT 1` de cette suite attraperait
// l'ancien client (encours 0) pendant que la vente partirait sur le nouveau.
// créances/règlements sont déjà vides à ce stade (cascade du jeu d'essai).
psql(`DELETE FROM clients WHERE nom = 'Client Credit C13';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);
console.log("Base prête.\n");

const navigateur = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || "chrome" });

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

  // Le crédit client (point b, activé le 2026-09-25) suit le paramètre de
  // boutique : présent dans la liste SEULEMENT si `credit_client_actif` vaut
  // 'oui'. L'ancien contrôle « jamais proposé » contredisait 045 — remplacé
  // par une vérification du paramètre réel (toujours vraie, quel que soit
  // le réglage de la boutique testée). La suite crédit du cycle 56 (PR #73)
  // exige en plus que l'option soit proposée quand le jeu d'essai active le
  // paramètre : c'est le cas ici (00_jeu_essai.sql), donc les deux lectures
  // restent vérifiées par ce même contrôle.
  const creditActif = psqlValeur(
    "SELECT valeur FROM parametres WHERE cle = 'credit_client_actif'"
  ) === "oui";
  const optionsPaiement = await page.locator("#paiement option").allTextContents();
  verifier(
    optionsPaiement.some((t) => /crédit/i.test(t)) === creditActif,
    `vente : présence du crédit client conforme au paramètre serveur (${creditActif ? "actif" : "inactif"})`
  );
  verifier(creditActif, "vente : jeu d'essai avec crédit client actif (attendu de la suite crédit cycle 56)");

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
  verifier(corpsVente.remise_totale === 0 && !(await page.isVisible("#ligne-remise-globale")),
    "vente sans remise : aucune remise en base, aucune ligne de remise affichée");
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
// 1 bis. Comptable : remises (cycle 59) — par ligne et globale
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);

  await page.fill("#recherche", "ciment");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.getElementById("panier").textContent.includes("Ciment"), { timeout: 5000 });

  // Remise PAR LIGNE : F3 (raccourci validé UX-2) puis prix négocié
  // 6 200 contre 6 500 au catalogue -> 300 FCFA d'écart affichés sous la
  // ligne, exactement la valeur que le serveur enregistrera en remise.
  await page.keyboard.press("F3");
  await page.keyboard.press("Control+A");
  await page.keyboard.type("6200");
  await page.keyboard.press("Enter");
  const texteLigne = await page.textContent("#panier");
  verifier(texteLigne.includes("remise 300 FCFA (4,6 %)"),
    `remise par ligne : écart au catalogue affiché sous l'article ("${texteLigne.trim()}")`);

  await page.fill("#numero-facturier", "MAG-REMISE01");
  await page.selectOption("#vendeur", "1");

  // Remise GLOBALE : 1 000 FCFA -> lignes d'aperçu et total réduit, avant
  // toute validation (même formule que le serveur, TVA extraite du total).
  await page.fill("#remise-globale", "1000");
  verifier(await page.isVisible("#ligne-remise-globale"), "remise globale : ligne « Remise sur la vente » visible");
  const texteRemiseGlobale = await page.textContent("#ligne-remise-globale");
  verifier(/1\s000 FCFA/.test(texteRemiseGlobale), `remise globale : montant affiché ("${texteRemiseGlobale.trim()}")`);
  verifier(await page.isVisible("#ligne-total-articles"), "remise globale : total articles TTC affiché avant remise");
  const apercuTotalRemise = await page.textContent("#total-ttc");
  const apercuTvaRemise = await page.textContent("#montant-tva");
  verifier(apercuTotalRemise === fcfaAttendu(5200),
    `remise globale : total réduit avant validation (${apercuTotalRemise})`);

  // Remise atteignant le total : refusée AVANT tout envoi — même règle que
  // le serveur (décision 2026-09-23 : c'est l'article offert qui couvre ce cas).
  let envoisVentes = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/ventes") && r.method() === "POST") envoisVentes++;
  });
  await page.fill("#remise-globale", "6200");
  verifier(await page.isVisible("#zone-erreur-remise"),
    "remise globale : avertissement immédiat quand elle atteint le total");
  await page.keyboard.press("F9");
  await page.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  const messageRemiseRefusee = await page.textContent("#zone-confirmation");
  verifier(/remise globale/i.test(messageRemiseRefusee),
    `remise globale refusée : message explicite ("${messageRemiseRefusee}")`);
  verifier(envoisVentes === 0, "remise globale refusée : aucun POST /ventes envoyé");

  // Remise valide : 1 000 FCFA -> double F9, vente réelle.
  await page.fill("#remise-globale", "1000");
  await page.keyboard.press("F9");
  await page.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  const messageConfirmation = await page.textContent("#zone-confirmation");
  verifier(/après remise de 1\s000 FCFA/.test(messageConfirmation),
    `remise globale : confirmation avec le montant ("${messageConfirmation}")`);
  const [reponseRemise] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/ventes") && r.request().method() === "POST", { timeout: 10000 }),
    page.keyboard.press("F9"),
  ]);
  verifier(reponseRemise.ok(), "vente avec remises : POST /ventes -> 201");
  const corpsRemise = await reponseRemise.json();
  verifier(corpsRemise.remise_totale === 1300,
    `vente avec remises : remise totale serveur = 1 300 FCFA (300 ligne + 1 000 globale) (${corpsRemise.remise_totale})`);
  verifier(
    apercuTotalRemise === fcfaAttendu(corpsRemise.total_ttc) && apercuTvaRemise === fcfaAttendu(corpsRemise.montant_tva),
    `vente avec remises : aperçu avant validation = confirmation serveur `
    + `(${apercuTotalRemise} / ${apercuTvaRemise} vs ${fcfaAttendu(corpsRemise.total_ttc)} / ${fcfaAttendu(corpsRemise.montant_tva)})`
  );
  await page.waitForFunction(() => !document.getElementById("zone-succes").hidden, { timeout: 10000 });
  const messageSuccesRemise = await page.textContent("#zone-succes");
  verifier(/Remise totale : 1\s300 FCFA/.test(messageSuccesRemise),
    `vente avec remises : message de succès avec la remise ("${messageSuccesRemise}")`);

  // Base réelle : les deux mécanismes sont bien distincts et persistés.
  const remiseGlobaleDb = psqlValeur(
    "SELECT remise_globale_montant FROM ventes WHERE numero_facturier = 'MAG-REMISE01'"
  );
  verifier(parseFloat(remiseGlobaleDb) === 1000,
    `base réelle : ventes.remise_globale_montant = 1 000 (${remiseGlobaleDb})`);
  const ligneDb = psqlValeur(
    "SELECT prix_catalogue || '|' || remise_montant || '|' || prix_unitaire "
    + "FROM ventes_lignes vl JOIN ventes v ON v.id = vl.vente_id "
    + "WHERE v.numero_facturier = 'MAG-REMISE01'"
  );
  verifier(/^6500\.00\|300\.00\|6200\.00$/.test(ligneDb),
    `base réelle : ligne catalogue/remise/payé = 6500/300/6200 (${ligneDb})`);

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

// ============================================================================
// 4. Crédit client : parcours complet de bout en bout (point b, cycle 54)
//    — vente à crédit depuis l'écran, créance visible, règlement partiel,
//      annulation refusée après règlement, annulation acceptée sur une vente
//      à crédit non réglée, retour marchandise sur vente à crédit : réduit
//      D'ABORD la créance restante, seul l'excédent au-delà du restant dû
//      devient un remboursement espèces réel (règle du propriétaire
//      2026-09-26, migration 047 — un acompte versé puis un retour complet
//      doit rendre l'acompte au client, jamais la valeur totale de la vente).
// ============================================================================
{
  const contexte = await navigateur.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await contexte.newPage();
  await seConnecter(page, "resp", MDP_RESPONSABLE);

  // --- Création d'un client depuis l'écran clients.html ---
  await page.goto(`${SERVEUR_URL}/app/clients.html`, { waitUntil: "networkidle" });
  await page.click("#bouton-nouveau-client");
  await page.fill("#f-nom", "Client Credit C13");
  await page.fill("#f-plafond", "500000");
  await page.locator("#panneau-contenu button").last().click();
  await page.waitForSelector("#zone-succes-panneau:not([hidden])", { timeout: 10000 });
  await page.waitForFunction(
    () => document.getElementById("liste-clients").textContent.includes("Client Credit C13"),
    { timeout: 5000 }
  );
  verifier(true, "crédit : client créé depuis clients.html et visible dans la liste");
  const clientId = psqlValeur("SELECT id FROM clients WHERE nom = 'Client Credit C13' LIMIT 1;");

  // --- Vente à crédit depuis l'écran de vente ---
  await page.goto(`${SERVEUR_URL}/app/vente.html`, { waitUntil: "networkidle" });
  await page.selectOption("#site-vente", "1");
  await page.fill("#recherche", "ciment");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.getElementById("panier").textContent.includes("Ciment"), { timeout: 5000 });
  await page.fill("#numero-facturier", "MAG-CRED01");
  await page.selectOption("#vendeur", "1");
  await page.selectOption("#paiement", "credit_client");
  await page.waitForFunction(() => !document.getElementById("champ-client").hidden, { timeout: 5000 });
  await page.selectOption("#client-credit", { label: "Client Credit C13" });
  await page.keyboard.press("F9");
  await page.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  const [reponseCredit] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/ventes") && r.request().method() === "POST", { timeout: 10000 }),
    page.keyboard.press("F9"),
  ]);
  verifier(reponseCredit.ok(), "crédit : vente à crédit depuis l'écran -> POST /ventes 201");
  const corpsCredit = await reponseCredit.json();
  const venteCreditId = corpsCredit.vente_id;
  await page.waitForFunction(() => !document.getElementById("zone-succes").hidden, { timeout: 10000 });
  verifier(true, "crédit : message de succès affiché après la vente à crédit");
  const creancesAvant = Number(psqlValeur("SELECT count(*) FROM creances WHERE vente_id = " + venteCreditId + ";"));
  verifier(creancesAvant === 1, "crédit : une créance a été créée pour la vente à crédit");

  // --- Créance visible sur l'écran clients.html ---
  await page.goto(`${SERVEUR_URL}/app/clients.html`, { waitUntil: "networkidle" });
  const ligneClient = page.locator("#liste-clients li", { hasText: "Client Credit C13" }).first();
  verifier(await ligneClient.count() > 0, "crédit : client listé avec son encours");
  const texteLigne = await ligneClient.textContent();
  verifier(/encours/.test(texteLigne), `crédit : l'encours est affiché sur la ligne du client (${texteLigne.trim().slice(0, 60)}…)`);

  // --- Règlement partiel depuis l'écran clients.html ---
  const montantCreance = Number(psqlValeur(`SELECT montant FROM creances WHERE vente_id = ${venteCreditId};`));
  const montantReglement = Math.floor(montantCreance / 2);
  await ligneClient.getByRole("button", { name: "Régler" }).click();
  await page.fill("#f-montant-reglement", String(montantReglement));
  await page.locator("#panneau-contenu button").last().click();
  await page.waitForSelector("#zone-succes-panneau:not([hidden])", { timeout: 10000 });
  verifier(true, "crédit : règlement partiel enregistré depuis l'écran");
  const reglementsCount = Number(psqlValeur(`SELECT count(*) FROM reglements_creances WHERE client_id = ${clientId};`));
  verifier(reglementsCount === 1, "crédit : un règlement est enregistré en base");
  const encoursApresReglement = Number(psqlValeur(`SELECT encours_client(${clientId});`));
  verifier(encoursApresReglement === montantCreance - montantReglement,
    `crédit : l'encours a diminué du règlement partiel (encours ${encoursApresReglement}, attendu ${montantCreance - montantReglement})`);

  // --- Annulation refusée après règlement (FIFO) ---
  const annulationRefusee = await page.evaluate(async (id) => {
    const session = JSON.parse(sessionStorage.getItem("qf_session"));
    const r = await fetch(`/ventes/${id}/annuler`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + session.jeton },
      body: JSON.stringify({ motif: "Tentative d'annulation après règlement" }),
    });
    return { statut: r.status, corps: await r.json() };
  }, venteCreditId);
  verifier(annulationRefusee.statut >= 400,
    `crédit : annulation après règlement refusée (statut ${annulationRefusee.statut})`);

  // --- Seconde vente à crédit, NON réglée -> annulation acceptée ---
  await page.goto(`${SERVEUR_URL}/app/vente.html`, { waitUntil: "networkidle" });
  await page.selectOption("#site-vente", "1");
  await page.fill("#recherche", "ciment");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.getElementById("panier").textContent.includes("Ciment"), { timeout: 5000 });
  await page.fill("#numero-facturier", "MAG-CRED02");
  await page.selectOption("#vendeur", "1");
  await page.selectOption("#paiement", "credit_client");
  await page.waitForFunction(() => !document.getElementById("champ-client").hidden, { timeout: 5000 });
  await page.selectOption("#client-credit", { label: "Client Credit C13" });
  await page.keyboard.press("F9");
  await page.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  const [reponseCredit2] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/ventes") && r.request().method() === "POST", { timeout: 10000 }),
    page.keyboard.press("F9"),
  ]);
  verifier(reponseCredit2.ok(), "crédit : seconde vente à crédit -> POST /ventes 201");
  const venteNonRegleeId = (await reponseCredit2.json()).vente_id;

  const annulationAcceptee = await page.evaluate(async (id) => {
    const session = JSON.parse(sessionStorage.getItem("qf_session"));
    const r = await fetch(`/ventes/${id}/annuler`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + session.jeton },
      body: JSON.stringify({ motif: "Annulation d'une vente à crédit non réglée" }),
    });
    return { statut: r.status, corps: await r.json() };
  }, venteNonRegleeId);
  verifier(annulationAcceptee.statut < 400,
    `crédit : annulation acceptée sur vente à crédit non réglée (statut ${annulationAcceptee.statut})`);
  const creanceAnnulee = psqlValeur(`SELECT annulee::text FROM creances WHERE vente_id = ${venteNonRegleeId};`);
  verifier(creanceAnnulee === "true", "crédit : la créance de la vente annulée est marquée annulée");

  // --- Retour marchandise COMPLET sur la vente à crédit partiellement
  // réglée : la créance est réduite du restant dû (montant_retourne, append-
  // only), et le remboursement espèces ne porte QUE sur l'excédent — la part
  // réellement encaissée par la boutique (l'acompte). La part à crédit n'a
  // jamais été encaissée : la rembourser serait une dépense fantôme, le
  // défaut exact que la migration 047 corrige (règle propriétaire 2026-09-26).
  await page.goto(`${SERVEUR_URL}/app/stock.html`, { waitUntil: "networkidle" });
  await page.fill("#recherche", "ciment");
  const ligneCiment = page.locator("#liste-articles li", { hasText: "Ciment" }).first();
  await ligneCiment.getByRole("button", { name: "Retour client", exact: true }).click();
  await page.waitForSelector("#carte-panneau:not([hidden])", { timeout: 5000 });
  await page.fill("#f-quantite", "1");
  await page.fill("#f-vente-id", String(venteCreditId));
  await page.selectOption("#f-issue", "remboursement_especes");
  await page.selectOption("#f-etat", "invendable");
  await page.locator("#panneau-contenu button").last().click();
  await page.waitForSelector("#zone-succes-panneau:not([hidden])", { timeout: 10000 });
  verifier(true, "crédit : retour marchandise déclaré sur la vente à crédit");

  await page.goto(`${SERVEUR_URL}/app/declarations.html`, { waitUntil: "networkidle" });
  const ligneRetour = page.locator("#liste-retours li", { hasText: "vente n°" + venteCreditId }).first();
  verifier(await ligneRetour.count() > 0, "crédit : le retour sur vente à crédit apparaît en attente");
  const encoursAvantRetour = Number(psqlValeur(`SELECT encours_client(${clientId});`));
  await ligneRetour.getByRole("button", { name: "Valider" }).click();
  const boutonRembourser = page.getByRole("button", { name: "Oui, rembourser" });
  verifier(await boutonRembourser.count() > 0, "crédit : confirmation explicite demandée pour le remboursement espèces");
  const [reponseValidationRetour] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/stock/retours-client/declarations/") && r.request().method() === "POST", { timeout: 10000 }),
    boutonRembourser.click(),
  ]);
  verifier(reponseValidationRetour.ok(), "crédit : validation du retour sur vente à crédit acceptée");
  await page.waitForFunction(() => document.querySelectorAll("#liste-retours li").length === 1, { timeout: 5000 });
  const encoursApresRetour = Number(psqlValeur(`SELECT encours_client(${clientId});`));
  verifier(encoursApresRetour < encoursAvantRetour,
    `crédit : le retour réduit la créance (encours ${encoursAvantRetour} -> ${encoursApresRetour})`);
  // Restant dû avant retour = créance − règlement partiel ; le retour est
  // COMPLET (1/1 unité), donc valeur_retour = montantCreance et l'excédent
  // en espèces vaut exactement l'acompte versé par le client.
  const montantRetourne = Number(psqlValeur(`SELECT montant_retourne FROM creances WHERE vente_id = ${venteCreditId};`));
  verifier(montantRetourne === montantCreance - montantReglement,
    `crédit : la créance est réduite du restant dû, pas de la valeur totale (montant_retourne ${montantRetourne})`);
  const depensesApres = Number(psqlValeur(`SELECT COALESCE(SUM(montant), 0) FROM transactions WHERE vente_id = ${venteCreditId} AND type = 'depense';`));
  verifier(depensesApres === montantReglement,
    `crédit : le remboursement espèces vaut exactement l'acompte réellement payé (${depensesApres} FCFA, jamais les ${montantCreance} de la vente)`);

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
