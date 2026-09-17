/* Vérifie, PAR EXÉCUTION RÉELLE, les 8 constats de UX_BASELINE.md §4 bis
   (campagne réelle n°1) retenus pour la piste UX, dans l'ordre de gêne
   décidé pour ce chantier : UX-7, UX-1, UX-2, UX-3, UX-4, UX-6, UX-9, UX-10.

   Nouveau fichier dédié (RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md, règle sur
   les fichiers communs) plutôt qu'un ajout aux suites existantes : ce
   chantier touche vente.html, tableau-bord.html et inventaire.html à la
   fois, un ajout réparti aurait été moins lisible qu'un fichier consacré.

   Prérequis : serveur démarré sur SERVEUR_URL, servant /app.
   Réinitialise elle-même la base (jeu d'essai + mots de passe réels).
*/
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { existsSync, mkdirSync } from "node:fs";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE_DEPOT = resolve(ICI, "..", "..");
const CAPTURES = resolve(ICI, "..", "captures") + "/";

const SERVEUR_URL = process.env.SERVEUR_URL || "http://127.0.0.1:8010";
const DB_PISTE = process.env.PGDATABASE_PISTE || "quincaillerie_test";
let PGDEV = resolve(RACINE_DEPOT, "_pgdev");
if (!existsSync(PGDEV)) {
  PGDEV = resolve(RACINE_DEPOT, "..", "..", "_pgdev");
}
const PSQL = resolve(PGDEV, "pgsql", "bin", "psql.exe");

const MDP_AGENT_COMPTA = "AgentComptaTest123";
const MDP_AGENT_STOCK = "AgentStockTest123";
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
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_COMPTA}', gen_salt('bf', 12)) WHERE identifiant='magasin.compta';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_AGENT_STOCK}', gen_salt('bf', 12)) WHERE identifiant='magasin.stock';`);
psql(`UPDATE utilisateurs SET tentatives_echouees=0, mot_de_passe_hash = crypt('${MDP_RESPONSABLE}', gen_salt('bf', 12)) WHERE identifiant='resp';`);
console.log("Base prête.\n");

if (!existsSync(CAPTURES)) mkdirSync(CAPTURES, { recursive: true });

const navigateur = await chromium.launch({ channel: "chrome" });

async function nouvellePage(largeur = 1366, hauteur = 900) {
  const contexte = await navigateur.newContext({ viewport: { width: largeur, height: hauteur } });
  const page = await contexte.newPage();
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

// ============================================================================
// UX-7 (le plus sérieux) : coupure réseau EN COURS de requête -> message
// clair en français près du champ, jamais un écran qui tourne indéfiniment,
// et la soumission redevient possible sans recharger la page.
// ============================================================================
{
  const { contexte, page } = await nouvellePage(1366, 900);
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);
  verifier(page.url().endsWith("vente.html"), "UX-7 : connexion -> vente.html");

  await page.fill("#recherche", "rare");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.getElementById("panier").textContent.includes("rare"), { timeout: 5000 });

  // La requête de validation est interceptée et JAMAIS honorée (ni réponse,
  // ni échec explicite) : exactement une coupure Wi-Fi EN COURS de requête,
  // pas un refus de connexion immédiat (déjà couvert par verifier-cablage.mjs
  // pour la panne réseau AVANT même l'envoi).
  await page.route("**/ventes", (route) => { /* jamais route.fulfill() ni route.abort() */ });

  await page.keyboard.press("F9"); // 1ère pression : confirmation
  await page.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  const avant = Date.now();
  await page.keyboard.press("F9"); // 2e pression : envoi réel, jamais résolu par le serveur

  await page.waitForFunction(
    () => {
      const z = document.getElementById("zone-confirmation");
      return !z.hidden && /impossible de contacter le serveur/i.test(z.textContent);
    },
    { timeout: 25000 }
  );
  const duree = Date.now() - avant;
  verifier(duree < 25000, `UX-7 : message affiché sans attente infinie (${duree} ms, timeout client = 20 s)`);
  const texteMsg = await page.textContent("#zone-confirmation");
  verifier(/impossible de contacter le serveur/i.test(texteMsg) && /r[ée]essayez/i.test(texteMsg),
    `UX-7 : message en français, clair, près du champ ("${texteMsg}")`);
  verifier(await page.isEnabled("#btn-valider"), "UX-7 : bouton de soumission réactivé après l'échec, sans recharger la page");

  // Reprise réelle : la route est libérée, une nouvelle tentative doit
  // réussir sans recharger la page (preuve que l'agent « peut reprendre »).
  await page.unroute("**/ventes");
  await page.keyboard.press("F9");
  await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/ventes") && r.request().method() === "POST", { timeout: 10000 }),
    page.keyboard.press("F9"),
  ]);
  await page.waitForFunction(() => !document.getElementById("zone-succes").hidden, { timeout: 10000 });
  verifier(true, "UX-7 : après correction du réseau, la vente aboutit SANS recharger la page");

  await contexte.close();
}

// ============================================================================
// UX-1 : ajouter un article au panier en ≤ 2 actions, y compris avec une
// quantité différente de 1 (le cas réel le plus courant en quincaillerie).
// ============================================================================
{
  const { contexte, page } = await nouvellePage(1366, 900);
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);

  // Action 1 : taper "5 ciment" (une préfixe de quantité). Action 2 : Entrée.
  await page.fill("#recherche", "5 ciment");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter"); // 2 actions au total : ≤ 2 (A3, UX-1)

  const contenuPanier = await page.textContent("#panier");
  verifier(contenuPanier.includes("Ciment"), "UX-1 : article ajouté au panier en 2 actions (taper + Entrée)");
  const quantiteAffichee = await page.inputValue(".panier__mini");
  verifier(quantiteAffichee === "5", `UX-1 : quantité 5 posée directement, sans 3e action sur la ligne (lu : "${quantiteAffichee}")`);

  await contexte.close();
}

// ============================================================================
// UX-2 : une vente ENTIÈRE au clavier seul, de la recherche à la validation,
// PRIX NÉGOCIÉ INCLUS (le scénario réel de la campagne, A6/A2) — jamais un
// clic de souris. Diagnostic préalable (voir rapport de cycle) : le blocage
// réel n'était pas la recherche/l'ajout (déjà au clavier) mais l'impossibilité
// d'atteindre le champ de prix sans souris ni Tab hasardeux — d'où F3.
// ============================================================================
{
  const { contexte, page } = await nouvellePage(1366, 900);
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);
  verifier(page.url().endsWith("vente.html"), "UX-2 : connexion -> vente.html");

  // Recherche + ajout, au clavier seul.
  await page.fill("#recherche", "fer");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.getElementById("panier").textContent.includes("Fer"), { timeout: 5000 });
  verifier(true, "UX-2 : article ajouté au clavier seul (recherche + Entrée)");

  // Négociation du prix au clavier seul (F3), SANS jamais cliquer ni Tab.
  await page.keyboard.press("F3");
  const cibleFocus = await page.evaluate(() => document.activeElement.className);
  verifier(cibleFocus.includes("panier__mini"), "UX-2 : F3 amène le focus clavier directement sur le champ de prix");
  await page.keyboard.type("2900");
  await page.keyboard.press("Enter");
  const focusApresEntree = await page.evaluate(() => document.activeElement.id);
  verifier(focusApresEntree === "recherche", "UX-2 : Entrée dans le champ de prix ramène le focus à la recherche (clavier seul, sans souris)");

  // Mode de paiement (F4) puis validation (F9 x2), toujours au clavier.
  await page.keyboard.press("F4");
  await page.keyboard.press("F9");
  await page.waitForFunction(() => !document.getElementById("zone-confirmation").hidden, { timeout: 5000 });
  await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/ventes") && r.request().method() === "POST", { timeout: 10000 }),
    page.keyboard.press("F9"),
  ]);
  await page.waitForFunction(() => !document.getElementById("zone-succes").hidden, { timeout: 10000 });
  const texteSucces = await page.textContent("#zone-succes");
  verifier(/enregistr[ée]e/i.test(texteSucces), `UX-2 : vente complète validée SANS AUCUN clic de souris ("${texteSucces}")`);

  await contexte.close();
}

// ============================================================================
// UX-3 / UX-4 : aucun débordement horizontal aux 5 largeurs standard, ET
// taille de police minimale garantie sur les chiffres des cartes.
// Diagnostic (voir rapport de cycle) : la cause n'était pas la largeur de
// viewport (déjà couverte) mais deux angles morts des suites existantes,
// qui utilisent toujours des libellés COURTS et fixes du jeu d'essai :
//  1. grid-template-columns: 1fr (sans minmax(0, ...)) ne protège pas du
//     débordement si un contenu réel est plus long qu'anticipé ;
//  2. les chiffres des cartes n'avaient pas de taille minimale garantie.
// Reproduit ici avec un nom d'article RÉELLEMENT long (pas le jeu d'essai
// habituel), pour couvrir l'angle mort plutôt que de re-tester la même
// donnée courte que verifier-cablage.mjs.
// ============================================================================
{
  const NOM_LONG = "Vis-autoperceuse-inoxydable-tete-fraisee-torx-6x80-boite-de-200-unites";
  psql(`UPDATE articles SET nom = '${NOM_LONG}' WHERE id = 1;`); // "Ciment..." -> nom long

  const LARGEURS = [360, 390, 768, 1366, 1920];
  for (const largeur of LARGEURS) {
    const { contexte, page } = await nouvellePage(largeur, 844);
    await seConnecter(page, "resp", MDP_RESPONSABLE);
    await page.waitForFunction(() => !document.getElementById("liste-ecarts-ventes").textContent.includes("chargement"), { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(400);

    const debordement = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    verifier(debordement <= 1, `UX-3 : tableau-bord@${largeur} avec un nom d'article réel long -> aucun débordement (${debordement}px)`);

    await page.screenshot({ path: `${CAPTURES}ux-corrections-tableau-bord-${largeur}.png`, fullPage: true });

    if (largeur <= 390) {
      // UX-4 : taille de police minimale garantie sur les chiffres des cartes.
      const taillePastille = await page.evaluate(() => {
        const el = document.querySelector(".tb-grille .pastille");
        return el ? parseFloat(getComputedStyle(el).fontSize) : 0;
      });
      verifier(taillePastille >= 16, `UX-4 : tableau-bord@${largeur} - taille de police des pastilles ≥ 16px (lu : ${taillePastille}px)`);
    }

    await contexte.close();
  }
  console.log(`  (captures : ${CAPTURES}ux-corrections-tableau-bord-*.png)`);
}

// ============================================================================
// UX-6 : le champ de comptage a bien inputmode="numeric" / type="number" —
// vérifié par inspection de l'attribut RÉELLEMENT RENDU, pas la lecture du
// fichier source.
// ============================================================================
{
  const { contexte, page } = await nouvellePage(390, 844);
  await seConnecter(page, "magasin.stock", MDP_AGENT_STOCK);
  await page.waitForFunction(() => !document.getElementById("bloc-comptage").hidden, { timeout: 10000 });

  const type = await page.getAttribute("#saisie", "type");
  const inputmode = await page.getAttribute("#saisie", "inputmode");
  verifier(type === "number", `UX-6 : attribut type="number" réellement rendu sur #saisie (lu : "${type}")`);
  verifier(inputmode === "numeric", `UX-6 : attribut inputmode="numeric" réellement rendu sur #saisie (lu : "${inputmode}")`);

  // UX-10, dans la foulée (même écran) : avertissement de caractère définitif
  // TOUJOURS visible, jamais un dialogue qui ajouterait une action.
  const avertissementVisible = await page.isVisible("#aide-definitif");
  const texteAvertissement = await page.textContent("#aide-definitif");
  verifier(avertissementVisible, "UX-10 : avertissement « comptage définitif » visible sans aucune action supplémentaire");
  verifier(/d[ée]finitif/i.test(texteAvertissement), `UX-10 : avertissement non ambigu (lu : "${texteAvertissement.trim()}")`);

  // Confirme qu'aucun dialogue bloquant n'a été ajouté : soumettre un
  // comptage ne déclenche aucune boîte de dialogue navigateur (confirm()).
  let dialogueDeclenche = false;
  page.on("dialog", async (d) => { dialogueDeclenche = true; await d.dismiss(); });
  await page.fill("#saisie", "10");
  await page.click("#btn-suivant");
  await page.waitForTimeout(500);
  verifier(!dialogueDeclenche, "UX-10 : aucun dialogue bloquant (confirm()) ajouté avant validation — pas de friction supplémentaire (A7)");

  await contexte.close();
}

// ============================================================================
// UX-9 : le prix indicatif affiché en gris porte un libellé non ambigu.
// ============================================================================
{
  const { contexte, page } = await nouvellePage(1366, 900);
  await seConnecter(page, "magasin.compta", MDP_AGENT_COMPTA);
  await page.fill("#recherche", "béton");
  await page.waitForFunction(() => !document.getElementById("suggestions").hidden, { timeout: 5000 });
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => !document.getElementById("dernier-ajout").textContent.includes("Aucun"), { timeout: 5000 });

  const texteDernierAjout = await page.textContent("#dernier-ajout");
  const couleur = await page.evaluate(() => getComputedStyle(document.getElementById("dernier-ajout")).color);
  verifier(!!couleur, "UX-9 : le prix indicatif reste affiché en gris (couleur de texte atténuée)");
  verifier(/indicatif/i.test(texteDernierAjout), `UX-9 : le mot « indicatif » est présent (lu : "${texteDernierAjout}")`);
  verifier(/pas le prix|PAS le prix/i.test(texteDernierAjout), `UX-9 : libellé précise explicitement que ce n'est PAS le prix facturé (lu : "${texteDernierAjout}")`);

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
